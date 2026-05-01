# SPEC.md — ED Triage Streamlit Dashboard

**👤 5% Bchan · 🤖 95% agent**

## Goal
Ship the locked [DASHBOARD.md](computer:///Users/anixlynch/dev/ER/DASHBOARD.md) as a working Streamlit app. Pre-generate triage assessments for the 10 cases in `inputs/patients.json`, render the two-column input/output layout, traffic-light action buckets, constraint panel from `ed_state.json`.

**Workflow order:** engine prompt → generate 10 assessments → streamlit app reads them → run.

## Inputs

| Need | File | Status | Who |
|------|------|--------|-----|
| ANTHROPIC_API_KEY | ~/.config/secrets/global.env | ✅ | AI |
| 10 patient cases | [inputs/patients.json](computer:///Users/anixlynch/dev/ER/inputs/patients.json) | ✅ | AI (other agent) |
| ED state snapshot | [inputs/ed_state.json](computer:///Users/anixlynch/dev/ER/inputs/ed_state.json) | ✅ | AI |
| Guideline corpus (rule_ids for citations) | [inputs/guidelines.md](computer:///Users/anixlynch/dev/ER/inputs/guidelines.md) | ⬜ | AI — needs ≥ 5 ESI rules |

## Outputs

| Deliverable | File | Status |
|-------------|------|--------|
| Reference sample assessment | [outputs/sample_assessment.json](computer:///Users/anixlynch/dev/ER/outputs/sample_assessment.json) | ✅ |
| Pre-generated assessments × 10 | outputs/assessments/{case_id}.json | ⬜ |
| Triage engine | app/engine.py | ⬜ |
| Streamlit app | app/streamlit_app.py | ⬜ |

## Phase Gates

| # | Phase | Status | Who |
|---|-------|--------|-----|
| 0 | Lock DASHBOARD.md + sample assessment | ✅ | AI |
| 1 | Guideline corpus (≥ 5 rule_ids) | ⬜ | AI |
| 2 | Engine — Claude prompt + structured output | ⬜ | AI |
| 3 | Generate 10 assessments | ⬜ | AI |
| 4 | Streamlit app — renders DASHBOARD.md layout | ⬜ | AI |
| 5 | Ship — screencast or deploy | ⬜ | AI |

## File Map

```
ER/
├── DASHBOARD.md              ← UI spec (locked)
├── requirement.md            ← case study
├── SLA.md                    ← ship contract
├── SPEC.md                   ← this file
├── inputs/
│   ├── patients.json         ← 10 cases
│   ├── ed_state.json         ← sidebar capacity
│   └── guidelines.md         ← rule_id corpus
├── outputs/
│   ├── sample_assessment.json   ← reference shape
│   └── assessments/             ← 10 generated (Phase 3)
└── app/
    ├── engine.py             ← Claude triage call (Phase 2)
    └── streamlit_app.py      ← UI (Phase 4)
```

## B-turns Pending
None — Bchan unblocked. AI executes Phases 1–5.

## Session Start
Read DASHBOARD.md → SLA.md → SPEC.md → start at first ⬜ phase.
