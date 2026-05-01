# SLA.md — ED Triage Streamlit Dashboard

Why we started: ship the locked DASHBOARD.md as a working Streamlit app, demo over the 10 cases in `inputs/patients.json`.

## THE ONE METRIC THAT MATTERS

| metric | now | target |
|--------|-----|--------|
| streamlit_app_ships (renders all 10 patients with all 6 output panels) | ❌ | ✅ |

## PHASE 1 — Triage Engine

**File:** `app/engine.py`
**Done when:** running engine over each of the 10 patients in `inputs/patients.json` produces a JSON matching the 6 panels in DASHBOARD.md (urgency, constraints, hypotheses, actions, explanation, checklist).

## PHASE 2 — Pre-generated Assessments

**File:** `outputs/assessments/{case_id}.json` × 10
**Done when:** all 10 files exist + each has all 6 panels populated + at least one citation per assessment resolves to `inputs/guidelines.md`.

## PHASE 3 — Streamlit App

**File:** `app/streamlit_app.py`
**Done when:** `streamlit run app/streamlit_app.py` shows the DASHBOARD.md layout — sidebar with case list + ED load, two-column input/output, all 6 output panels render, traffic-light colors correct (🟢 safe / 🟡 caution / 🔴 urgent).

## PHASE 4 — Ship

**Done when:** any of: (a) screencast recorded, (b) deployed to Streamlit Community Cloud, or (c) `make demo` runs cleanly on a fresh checkout.
