# ED Triage Support — Streamlit Demo

Decision-support assistant for ED triage. Renders the locked layout in [DASHBOARD.md](DASHBOARD.md).

> **Decision support, not decision.** Cited rules, not opinions. Logged overrides, not a black box.

## 🚀 Live demo

**→ https://anix-lynch-er-appstreamlit-app-pmcbnk.streamlit.app/**

Sidebar lists 12 cases. Try **ER-0042** (chest pain, 🔴 NOW), **ER-0046** (finger lac, 🟢 WAIT), **ER-0049** (RLQ pain, 🟡 SOON), and the two adversarial cases **ER-0052 / ER-0053** to see how the assistant won't let normal-looking vitals or patient reassurance down-triage a real red flag.

## Run locally

```bash
pip install -r requirements.txt

# Activate key (per CLAUDE.md)
export ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY' ~/.config/secrets/global.env | cut -d'"' -f2)

# Pre-generate assessments (skipped if outputs/assessments/{id}.json already exists)
python -m app.engine

# Launch UI → http://localhost:8501
streamlit run app/streamlit_app.py
```

Or: `make demo`.

## Layout
- `inputs/patients.json` — 12 cases (ER-0042 → ER-0053; last 2 are adversarial)
- `inputs/ed_state.json` — bed/staff/queue snapshot for sidebar
- `inputs/guidelines.md` — 18 ESI v4 rule_ids the engine is allowed to cite
- `outputs/assessments/{case_id}.json` — pre-generated, one per case
- `app/engine.py` — Claude triage call (structured output via tool_use)
- `app/prompt.py` — system prompt + tool schema (bucket caps 3/2/1, rule citation contract)
- `app/streamlit_app.py` — UI; sidebar reads tier from each assessment file (single source of truth)

## Project state
- [DASHBOARD.md](DASHBOARD.md) — UI spec
- [SLA.md](SLA.md) — ship contract
- [SPEC.md](SPEC.md) — phase tracker
- [requirement.md](requirement.md) — case study spec
- [pitch.md](pitch.md) — CTO/CFO pitch deck
