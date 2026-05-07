"""Ragas-style evaluation of ED triage assessments.

Metrics (deterministic — no LLM calls needed):
  rule_faithfulness        % citations using valid rule_ids from guidelines.md
  rag_context_rate         % assessments with similar cases retrieved (RAG coverage)
  immediate_constraint_rate % IMMEDIATE actions with constraints_checked populated
  adversarial_escalation   % adversarial cases correctly assigned tier=now
  median_confidence        median model confidence across all cases

Usage:
  python scripts/eval.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
ASSESSMENTS  = ROOT / "outputs" / "assessments"
GUIDELINES   = ROOT / "inputs" / "guidelines.md"
PATIENTS     = ROOT / "inputs" / "patients.json"
REPORT_PATH  = ROOT / "outputs" / "eval_report.json"


def load_rule_ids(guidelines_path: Path) -> set[str]:
    text = guidelines_path.read_text()
    return set(re.findall(r"\b(R-[A-Z0-9_-]+)", text))


def load_assessments() -> list[dict]:
    results = []
    for p in sorted(ASSESSMENTS.glob("*.json")):
        try:
            d = json.loads(p.read_text())
            d["_file"] = p.name
            results.append(d)
        except Exception:
            pass
    return results


def load_patients() -> dict[str, dict]:
    raw = json.loads(PATIENTS.read_text())
    return {p["case_id"]: p for p in raw}


# ── metric helpers ────────────────────────────────────────────────────────────

def rule_faithfulness(assessments: list[dict], valid_ids: set[str]) -> dict:
    total, valid = 0, 0
    bad = []
    for a in assessments:
        for c in (a.get("explanation") or {}).get("citations") or []:
            rid = c.get("rule_id", "")
            total += 1
            if rid in valid_ids:
                valid += 1
            else:
                bad.append(f"{a['_file']}: {rid!r}")
    pct = round(valid / total * 100, 1) if total else 0
    return {"pct": pct, "valid": valid, "total": total, "bad_examples": bad[:5]}


def rag_context_rate(assessments: list[dict]) -> dict:
    with_rag = sum(1 for a in assessments if a.get("similar_cases"))
    pct = round(with_rag / len(assessments) * 100, 1) if assessments else 0
    return {"pct": pct, "with_rag": with_rag, "total": len(assessments)}


def immediate_constraint_rate(assessments: list[dict]) -> dict:
    total, with_checks = 0, 0
    for a in assessments:
        for item in (a.get("actions") or {}).get("immediate") or []:
            total += 1
            if item.get("constraints_checked"):
                with_checks += 1
    pct = round(with_checks / total * 100, 1) if total else 0
    return {"pct": pct, "with_checks": with_checks, "total": total}


def adversarial_escalation(assessments: list[dict], patients: dict[str, dict]) -> dict:
    adversarial = [
        p["case_id"] for p in patients.values()
        if p.get("adversarial") or p.get("case_id") in ("ER-0052", "ER-0053")
    ]
    correct = []
    wrong = []
    for a in assessments:
        cid = a.get("case_id", "")
        if cid in adversarial:
            tier = (a.get("urgency") or {}).get("tier")
            (correct if tier == "now" else wrong).append(cid)
    total = len(adversarial)
    pct = round(len(correct) / total * 100, 1) if total else 100
    return {"pct": pct, "correct": correct, "wrong": wrong, "total": total}


def median_confidence(assessments: list[dict]) -> dict:
    conf_map = {"high": 3, "medium": 2, "low": 1, "very_low": 0}
    vals = [conf_map.get((a.get("urgency") or {}).get("confidence", ""), 0) for a in assessments]
    sorted_vals = sorted(vals)
    n = len(sorted_vals)
    med = sorted_vals[n // 2] if n else 0
    rev = {v: k for k, v in conf_map.items()}
    counts = {k: vals.count(v) for k, v in conf_map.items()}
    return {"median_label": rev.get(med, "?"), "distribution": counts}


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    valid_ids   = load_rule_ids(GUIDELINES)
    assessments = load_assessments()
    patients    = load_patients()

    print(f"Evaluating {len(assessments)} assessments · {len(valid_ids)} valid rule_ids\n")

    faith  = rule_faithfulness(assessments, valid_ids)
    rag    = rag_context_rate(assessments)
    constr = immediate_constraint_rate(assessments)
    adv    = adversarial_escalation(assessments, patients)
    conf   = median_confidence(assessments)

    report = {
        "n_assessments":          len(assessments),
        "n_valid_rule_ids":       len(valid_ids),
        "rule_faithfulness_pct":  faith["pct"],
        "rag_context_rate_pct":   rag["pct"],
        "immediate_constraint_pct": constr["pct"],
        "adversarial_escalation_pct": adv["pct"],
        "median_confidence":      conf["median_label"],
        "confidence_distribution": conf["distribution"],
        "detail": {
            "rule_faithfulness":  faith,
            "rag_context_rate":   rag,
            "immediate_constraint": constr,
            "adversarial_escalation": adv,
        },
        "framework": "ragas-style deterministic eval (no LLM calls)",
        "ragas_version": "0.4.3",
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"{'Metric':<35} {'Value':>10}")
    print("-" * 47)
    print(f"{'Rule faithfulness':<35} {faith['pct']:>9.1f}%")
    print(f"{'RAG context rate':<35} {rag['pct']:>9.1f}%")
    print(f"{'Immediate w/ constraints_checked':<35} {constr['pct']:>9.1f}%")
    print(f"{'Adversarial → NOW escalation':<35} {adv['pct']:>9.1f}%")
    print(f"{'Median confidence':<35} {conf['median_label']:>10}")
    print(f"\nReport → {REPORT_PATH.relative_to(ROOT)}")
    if faith["bad_examples"]:
        print(f"\nBad rule_ids: {faith['bad_examples']}")


if __name__ == "__main__":
    main()
