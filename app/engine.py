"""Triage engine: read patients + ed_state + guidelines, call Claude, write assessments."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from app.prompt import SYSTEM_PROMPT, TOOL_SCHEMA, user_prompt

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"
OUT_DIR = ROOT / "outputs" / "assessments"
MODEL = "claude-opus-4-7"
RULE_PACK = "esi-v4-2026-05"


def load_inputs() -> tuple[list[dict], dict, str]:
    patients = json.loads((INPUTS / "patients.json").read_text())
    ed_state = json.loads((INPUTS / "ed_state.json").read_text())
    guidelines = (INPUTS / "guidelines.md").read_text()
    return patients, ed_state, guidelines


REQUIRED_BODY_KEYS = {"urgency", "constraints", "hypotheses", "actions", "explanation", "checklist", "review_note"}


def _unwrap(body: dict) -> dict:
    """Claude sometimes wraps tool input under {assessment: {...}} or {parameter: {...}}.
    If the body has exactly one key whose value is a dict containing the real fields, unwrap it."""
    if not isinstance(body, dict):
        return body
    # Direct hit — already has required fields at top level.
    if REQUIRED_BODY_KEYS & body.keys():
        return body
    # Single-key wrapper (any name) → unwrap if inner dict has required fields.
    if len(body) == 1:
        inner = next(iter(body.values()))
        if isinstance(inner, dict) and REQUIRED_BODY_KEYS & inner.keys():
            return inner
    return body


def assess_one(client: anthropic.Anthropic, patient: dict, ed_state: dict, guidelines: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": guidelines,    "cache_control": {"type": "ephemeral"}},
        ],
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "submit_assessment"},
        messages=[{"role": "user", "content": user_prompt(patient, ed_state, guidelines)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_assessment":
            body = _unwrap(block.input)
            missing = REQUIRED_BODY_KEYS - body.keys()
            if missing:
                raise RuntimeError(f"{patient.get('case_id')}: tool_use missing required keys {sorted(missing)}; got {sorted(body.keys())}")
            return body
    raise RuntimeError(f"No tool_use returned for {patient.get('case_id')}")


def wrap_assessment(patient: dict, body: dict) -> dict:
    return {
        "case_id":    patient["case_id"],
        "patient_id": patient["patient_id"],
        "encounter":  {"arrival_time": patient["arrival_time"]},
        "patient":    {"age": patient["age"], "sex": patient["sex"]},
        **body,
        "meta": {
            "model":        MODEL,
            "rule_pack":    RULE_PACK,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def main(case_filter: str | None = None) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set. Activate per CLAUDE.md, then re-run.")

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
        body = assess_one(client, patient, ed_state, guidelines)
        out_path.write_text(json.dumps(wrap_assessment(patient, body), indent=2, ensure_ascii=False))
        print(f"  wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
