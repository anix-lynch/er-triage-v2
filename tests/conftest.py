"""Shared pytest fixtures. No API calls — every external service is mocked."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_patient():
    return {
        "case_id": "ER-TEST-01",
        "age": 58,
        "sex": "male",
        "vitals": {"bp": "138/86", "hr": 92, "rr": 18, "spo2": 96, "temp": 37.0},
        "chief_complaint": "chest pain for 30 minutes",
        "nurse_note": "patient pale, mildly diaphoretic, anxious",
    }


@pytest.fixture
def sample_assessment():
    """Mirrors the shape of outputs/assessments/*.json — what engine.py produces."""
    return {
        "case_id": "ER-TEST-01",
        "tier": "now",
        "confidence": "high",
        "cited_rules": ["R-ESI-T1", "R-ACS-01", "R-TIME-ECG"],
        "constraints_checked": ["aspirin_allergy", "active_gi_bleed"],
        "rationale": "Chest pain with diaphoresis in a 58 y/o male; ACS rule-out per R-ACS-01.",
        "similar_cases": [
            {"case_id": "PAST-04", "esi_tier": 1, "outcome": "STEMI confirmed"},
        ],
    }


@pytest.fixture
def guidelines_text():
    """Real guidelines content from the repo — used for rule_faithfulness validation."""
    return (REPO / "inputs" / "guidelines.md").read_text()


@pytest.fixture
def real_assessments():
    """All real assessments committed to outputs/assessments/. Used for eval tests."""
    files = sorted((REPO / "outputs" / "assessments").glob("ER-*.json"))
    return [json.loads(f.read_text()) for f in files]
