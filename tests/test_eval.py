"""Tests for scripts/eval.py — deterministic metric verification. No API calls."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Import scripts/eval.py as a module without running its main()
_spec = importlib.util.spec_from_file_location("ed_eval", REPO / "scripts" / "eval.py")
_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_eval)  # type: ignore[union-attr]


# ---------- load_rule_ids ----------

def test_load_rule_ids_finds_known_ids():
    ids = _eval.load_rule_ids(REPO / "inputs" / "guidelines.md")
    assert isinstance(ids, set)
    assert len(ids) > 0
    # ESI tier rules must be present
    assert any(r.startswith("R-ESI") for r in ids), (
        f"Expected R-ESI-* rules in guidelines, got: {sorted(ids)[:5]}"
    )


# ---------- rule_faithfulness ----------

def test_rule_faithfulness_real_data_is_perfect():
    """Headline claim from README: 100% rule_faithfulness across n=12. Verify."""
    assessments = _eval.load_assessments()
    valid_ids = _eval.load_rule_ids(REPO / "inputs" / "guidelines.md")
    result = _eval.rule_faithfulness(assessments, valid_ids)
    assert result["pct"] == 100.0, (
        f"rule_faithfulness regressed: {result['pct']}%, bad={result['bad_examples']}"
    )
    assert result["valid"] == result["total"]


def test_rule_faithfulness_catches_fabricated_rule_id():
    """If a model hallucinates a rule_id, the metric must catch it."""
    fake_assessments = [{
        "_file": "ER-FAKE.json",
        "case_id": "ER-FAKE",
        "explanation": {"citations": [
            {"rule_id": "R-ESI-T1"},   # real
            {"rule_id": "R-MADE-UP"},  # fabricated
        ]}
    }]
    valid_ids = {"R-ESI-T1", "R-ESI-T2", "R-ACS-01"}
    result = _eval.rule_faithfulness(fake_assessments, valid_ids)
    assert result["pct"] == 50.0
    assert result["bad_examples"] and "R-MADE-UP" in result["bad_examples"][0]


# ---------- adversarial_escalation ----------

def test_adversarial_escalation_real_data_is_perfect():
    """Headline claim: ER-0052 and ER-0053 both → tier `now`. Verify."""
    assessments = _eval.load_assessments()
    patients = _eval.load_patients()
    result = _eval.adversarial_escalation(assessments, patients)
    assert result["pct"] == 100.0, (
        f"adversarial_escalation regressed: wrong={result['wrong']}, "
        f"correct={result['correct']}"
    )
    assert "ER-0052" in result["correct"]
    assert "ER-0053" in result["correct"]


def test_adversarial_escalation_catches_under_triage():
    """If a model under-triages an adversarial case, the metric must catch it."""
    patients = {
        "ER-0052": {"case_id": "ER-0052", "adversarial": True},
        "ER-0053": {"case_id": "ER-0053", "adversarial": True},
    }
    bad_assessments = [
        {"case_id": "ER-0052", "urgency": {"tier": "soon"}},  # WRONG — should be `now`
        {"case_id": "ER-0053", "urgency": {"tier": "now"}},   # correct
    ]
    result = _eval.adversarial_escalation(bad_assessments, patients)
    assert result["pct"] == 50.0
    assert "ER-0052" in result["wrong"]


# ---------- immediate_constraint_rate ----------

def test_immediate_constraint_rate_within_expected_range():
    """README claims 95.8%. Allow any value ≥90% as a soft regression guard."""
    assessments = _eval.load_assessments()
    result = _eval.immediate_constraint_rate(assessments)
    assert result["pct"] >= 90.0, (
        f"immediate_constraint_rate dropped to {result['pct']}% — investigate"
    )


# ---------- median_confidence ----------

def test_median_confidence_returns_valid_label():
    assessments = _eval.load_assessments()
    if not assessments:
        pytest.skip("no assessments to test against")
    result = _eval.median_confidence(assessments)
    assert "median_label" in result
    assert result["median_label"] in {"high", "medium", "low", "very_low", None}
    # And the distribution should sum to the total assessment count
    assert sum(result["distribution"].values()) == len(assessments)
