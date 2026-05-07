# ED Triage Decision Support — v2

> **Decision support, not decision.** Cited rules, not opinions. Logged overrides, not a black box.

[![Live demo](https://img.shields.io/badge/Live-Cloud_Run-green)](https://er-triage-v2-tjb2srbb2q-uw.a.run.app)
[![Hosting](https://img.shields.io/badge/GCP-Cloud_Run_us--west1-blue)]()
[![Eval](https://img.shields.io/badge/Ragas-rule_faithfulness_100%25-brightgreen)]()
[![Eval](https://img.shields.io/badge/Ragas-adversarial_escalation_100%25-brightgreen)]()

## 🟢 Live demo

**→ https://er-triage-v2-tjb2srbb2q-uw.a.run.app**

Hosted on Google Cloud Run · scale-to-zero · ~5s cold start · $0/month idle.
Click any of the 12 ER cases (sidebar) to see the triage assessment, cited ESI rule IDs, and similar past cases retrieved by RAG.

---

## What v2 demonstrates (vs v1 in-session prototype)

The v1 prototype (interview submission) was scoped live to demo-grade local Streamlit, no extra agent layer, synthetic data — and the close-of-loop was confirmed in-call and via email. v2 is the production hardening of that scope: the **same five capabilities the rubric flagged as "discussed not demonstrated"** are now shipped artifacts you can verify by clicking files in this repo.

| # | Station | v1 (in-session) | v2 (this repo) | Verify |
|---|---------|-----------------|----------------|--------|
| **1** | **Deployment** | local Streamlit | **Cloud Run + Docker + Artifact Registry, secret-mounted API key** | [`Dockerfile`](Dockerfile) · [`deploy/cloudrun.sh`](deploy/cloudrun.sh) · live URL above |
| **5** | **Vector DBs** | discussed | **Chroma persistent collection, 23 cases indexed** | [`app/retrieval/store.py`](app/retrieval/store.py) · [`app/retrieval/search.py`](app/retrieval/search.py) |
| **6** | **Embeddings** | discussed | **Vertex AI `gemini-embedding-001` (3072-dim) with SHA-256 cache** | [`app/retrieval/embed.py`](app/retrieval/embed.py) · [`outputs/embeddings/cache.json`](outputs/embeddings/cache.json) |
| **7** | **Data Extraction** | synthetic JSON only | **synthetic + 3 cases extracted from real ED PDF via pdfplumber** | [`scripts/gen_past_cases.py`](scripts/gen_past_cases.py) · [`inputs/past_cases/cases.json`](inputs/past_cases/cases.json) |
| **8** | **Memory** | discussed | **Firestore session log, persists across Cloud Run scale-to-zero** | [`app/memory.py`](app/memory.py) |

The four stations already at 4.0 in v1 (Eval, LLMs, Frameworks, Alignment & Observability) are preserved and verifiable here:

| # | Station | v2 evidence |
|---|---------|-------------|
| **2** | **Evaluation** (Ragas-style) | [`scripts/eval.py`](scripts/eval.py) · [`outputs/eval_report.json`](outputs/eval_report.json) — rule_faithfulness 100%, adversarial_escalation 100%, n=12 |
| **3** | **LLMs (thinking core)** | [`app/engine.py`](app/engine.py) · [`app/prompt.py`](app/prompt.py) · [`inputs/guidelines.md`](inputs/guidelines.md) — XML-tagged context, forced rule citation, JSON tool-use |
| **4** | **Frameworks / Orchestration** | [`app/engine.py`](app/engine.py) · [`inputs/ed_state.json`](inputs/ed_state.json) — RAG context + ED state injection + override capture |
| **9** | **Alignment & Observability** | [`app/guardrails.py`](app/guardrails.py) — regex injection filter, length cap, override logging |

Full file-to-station map: [`folder_structure_mapped.md`](folder_structure_mapped.md).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Cloud Run (us-west1)                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Streamlit UI (app/streamlit_app.py)                        │   │
│  │   - sidebar: 12 patients, ed_state snapshot                 │   │
│  │   - main: tier card · cited rules · similar past cases      │   │
│  │   - override panel → Firestore log (memory.py)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                  reads pre-generated assessments                    │
│                              ▼                                      │
│        outputs/assessments/ER-004*.json (12 cases, committed)       │
└─────────────────────────────────────────────────────────────────────┘

   Built offline (one-time, run locally with API key):
   ┌──────────────────────────────────────────────────────────────┐
   │  python -m app.engine                                        │
   │   patient.json + guidelines.md + ed_state.json               │
   │       │                                                      │
   │       ├─ embed query (Vertex gemini-embedding-001) ────┐     │
   │       │                                                ▼     │
   │       │                              Chroma top-k similar    │
   │       │                              past cases (RAG)        │
   │       ▼                                                      │
   │   prompt.py builds XML context  ←  similar_cases injected    │
   │       │                                                      │
   │       ▼                                                      │
   │   Claude (claude-sonnet-4-6) → JSON assessment              │
   │       │                                                      │
   │       ▼                                                      │
   │   outputs/assessments/{case_id}.json (committed to repo)     │
   └──────────────────────────────────────────────────────────────┘
```

### Why pre-generated assessments instead of live LLM-on-click?

This is a deliberate choice, not a shortcut:

- **Reproducibility** — every reviewer sees identical output, no model-drift-between-clicks.
- **Auditability** — every assessment is a committed JSON artifact you can `git diff`.
- **Cost** — $0 in LLM spend per visitor; the Cloud Run cost is just the Streamlit container ($0 idle, ~$0.40 per 1k requests).
- **Eval determinism** — `outputs/eval_report.json` reflects exactly what the demo shows.

The `engine.py` does call Claude at generation time. Click "regenerate locally" steps below to see the full live path.

---

## Eval results — Ragas-style (n=12)

Run: `python scripts/eval.py` · Full output: [`outputs/eval_report.json`](outputs/eval_report.json)

| Metric | Result | Notes |
|--------|--------|-------|
| **Rule faithfulness** | **100%** | Zero fabricated `rule_id`s — every citation exists in `guidelines.md` |
| **Adversarial escalation** | **100%** | ER-0052 + ER-0053 both → `now` despite normal-vitals / patient-reassurance traps |
| **Immediate w/ constraints checked** | 95.8% | Contraindication verification on almost all critical actions |
| **Median confidence** | high | Medium only on adversarial-by-design ER-0052 |

### Adversarial cases (where RAG matters most)

| Case | Trap | Tier | Confidence |
|------|------|------|------------|
| **ER-0052** Walter Brennan | Normal vitals + patient reassurance masking STEMI | `now` | medium |
| **ER-0053** Diana Chen | "It's just anxiety" with SpO₂ 89% | `now` | high |

RAG retrieves prior MI / silent-infarct / hypoxia-mistaken-for-anxiety cases, anchoring the model against the in-context reassurance bias.

---

## Try it (no install)

1. Click the **live URL** above.
2. Sidebar → pick any case. Try **ER-0042** (chest pain, NOW), **ER-0046** (finger lac, WAIT), **ER-0049** (RLQ pain, SOON), or the adversarial **ER-0052 / ER-0053**.
3. Note: assessment card · cited rule IDs (R-ESI-T1..T5, R-ACS-01, etc.) · similar past cases retrieved by RAG · override panel.

## Run locally (regenerate assessments against live Claude)

```bash
git clone https://github.com/anix-lynch/er-triage-v2 && cd er-triage-v2
pip install -r requirements.txt

cp .env.example .env  # then fill ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)

# (one-time) build the Chroma vector store from inputs/past_cases/cases.json
python scripts/build_index.py

# Regenerate all 12 assessments via live Claude + RAG retrieval
python -m app.engine

# Run the eval suite (Ragas-style, deterministic, no LLM calls)
python scripts/eval.py

# Launch UI → http://localhost:8501
streamlit run app/streamlit_app.py
```

Or: `make demo`.

## Re-deploy to Cloud Run

```bash
export GCP_PROJECT=<your-gcp-project>
bash deploy/cloudrun.sh
```

The script builds via Cloud Build → pushes to Artifact Registry → deploys to Cloud Run with `ANTHROPIC_API_KEY` mounted from Secret Manager. Vertex AI auth uses the Cloud Run service account (no key needed). Region defaults to `us-west1`.

---

## Repo layout

| Path | Purpose |
|------|---------|
| [`app/engine.py`](app/engine.py) | Triage loop: patient → prompt → Claude → JSON assessment |
| [`app/prompt.py`](app/prompt.py) | XML-tagged system prompt + tool schema, forces rule citation |
| [`app/guardrails.py`](app/guardrails.py) | Regex injection filter, length cap, override logging |
| [`app/memory.py`](app/memory.py) | Firestore session log (graceful no-op when Firestore unavailable) |
| [`app/streamlit_app.py`](app/streamlit_app.py) | UI shell, sidebar, override panel |
| [`app/retrieval/embed.py`](app/retrieval/embed.py) | Vertex `gemini-embedding-001` wrapper, SHA-256 cache |
| [`app/retrieval/store.py`](app/retrieval/store.py) | Chroma persistent collection |
| [`app/retrieval/search.py`](app/retrieval/search.py) | Embed query → cosine top-k → ranked similar cases |
| [`scripts/build_index.py`](scripts/build_index.py) | One-time indexer for `cases.json` → Chroma |
| [`scripts/eval.py`](scripts/eval.py) | Ragas-style deterministic eval, writes `outputs/eval_report.json` |
| [`scripts/gen_past_cases.py`](scripts/gen_past_cases.py) | PDF → structured case extraction (pdfplumber) |
| [`inputs/guidelines.md`](inputs/guidelines.md) | ESI v4 rule set injected verbatim into every prompt |
| [`inputs/patients.json`](inputs/patients.json) | 12 patient cases used in eval |
| [`inputs/ed_state.json`](inputs/ed_state.json) | ED beds/staff/queue snapshot |
| [`inputs/past_cases/cases.json`](inputs/past_cases/cases.json) | 23-case RAG corpus (20 synthetic + 3 PDF-extracted) |
| [`outputs/assessments/`](outputs/assessments) | 12 pre-generated JSONs — one per case, what the demo renders |
| [`outputs/eval_report.json`](outputs/eval_report.json) | Full Ragas output |
| [`Dockerfile`](Dockerfile) | python:3.12-slim, Streamlit on `:8080` |
| [`deploy/cloudrun.sh`](deploy/cloudrun.sh) | gcloud builds + run deploy + secret mount |
| [`folder_structure_mapped.md`](folder_structure_mapped.md) | File-to-station map (the Rosetta Stone) |
| [`DASHBOARD.md`](DASHBOARD.md) | UI layout spec |
| [`SPEC.md`](SPEC.md) | Phase tracker |
| [`pitch.md`](pitch.md) | CTO/CFO pitch deck |
