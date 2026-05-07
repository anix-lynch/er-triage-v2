"""Triage engine: read patients + ed_state + guidelines, call Claude, write assessments."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from app.prompt import SYSTEM_PROMPT, TOOL_SCHEMA, user_prompt
from app.retrieval.search import find_similar

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"
OUT_DIR = ROOT / "outputs" / "assessments"
MODEL = "claude-opus-4-7"
RULE_PACK = "esi-v4-2026-05"
USE_RAG = os.environ.get("USE_RAG", "true").lower() == "true"


def load_inputs():
    patients = json.loads((INPUTS / "patients.json").read_text())
    ed_state = json.loads((INPUTS / "ed_state.json").read_text())
    guidelines = (INPUTS / "guidelines.md").read_text()
    return patients, ed_state, guidelines


REQUIRED_BODY_KEYS = {"urgency", "constraints", "hypotheses", "actions", "explanation", "checklist", "review_note"}


def _unwrap(body):
    if not isinstance(body, dict):
        return body
    if REQUIRED_BODY_KEYS & body.keys():
        return body
    if len(body) == 1:
        inner = next(iter(body.values()))
        if isinstance(inner, dict) and REQUIRED_BODY_KEYS & inner.keys():
            return inner
    return body


def assess_one(client, patient, ed_state, guidelines, similar_cases=None):
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": guidelines,    "cache_control": {"type": "ephemeral"}},
        ],
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_assessment"},
        messages=[{"role": "user", "content": user_prompt(patient, ed_state, guidelines, similar_cases)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_assessment":
            body = _unwrap(block.input)
            missing = REQUIRED_BODY_KEYS - body.keys()
            if missing:
                raise RuntimeError(f"{patient.get('case_id')}: missing keys {sorted(missing)}")
            return body
    raise RuntimeError(f"No tool_use returned for {patient.get('case_id')}")


def _slim_similar(similar_cases):
    """Store only what the UI needs — avoid bloating assessment JSON."""
    if not similar_cases:
        return []
    out = []
    for m in similar_cases:
        meta = m.get("metadata", {})
        out.append({
            "case_id":    meta.get("case_id", m.get("case_id", "?")),
            "esi_tier":   meta.get("esi_tier", "?"),
            "outcome":    meta.get("outcome", "?"),
            "similarity": round(float(m.get("similarity", 0)), 4),
            "summary":    str(m.get("document", meta.get("summary", "")))[:300],
        })
    return out


def wrap_assessment(patient, body, similar_cases=None):
    result = {
        "case_id":    patient["case_id"],
        "patient_id": patient["patient_id"],
        "encounter":  {"arrival_time": patient["arrival_time"]},
        "patient":    {"age": patient["age"], "sex": patient["sex"]},
        **body,
        "meta": {
            "model":        MODEL,
            "rule_pack":    RULE_PACK,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rag_enabled":  USE_RAG,
        },
    }
    if similar_cases:
        result["similar_cases"] = _slim_similar(similar_cases)
    return result


def main(case_filter=None):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients, ed_state, guidelines = load_inputs()
    client = anthropic.Anthropic()

    targets = [p for p in patients if (case_filter is None or p["case_id"] == case_filter)]
    for patient in targets:
        out_path = OUT_DIR / f"{patient['case_id']}.json"
        if out_path.exists() and case_filter is None:
            print(f"skip {patient['case_id']} (exists)")
            continue
        print(f"assess {patient['case_id']} ({patient['name']})...", flush=True)
        similar = find_similar(patient, k=3) if USE_RAG else None
        if similar:
            print(f"  RAG: {len(similar)} similar cases retrieved", flush=True)
        body = assess_one(client, patient, ed_state, guidelines, similar)
        out_path.write_text(json.dumps(wrap_assessment(patient, body, similar), indent=2, ensure_ascii=False))
        print(f"  wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
