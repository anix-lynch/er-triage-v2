# ER2 — Folder Structure × Dinesh Scorecard

> **🟢 LIVE DEMO:** https://er-triage-v2-tjb2srbb2q-uw.a.run.app
> **📦 Public repo:** https://github.com/anix-lynch/er-triage-v2
> **☁️ Hosting:** Google Cloud Run · `us-west1` · scale-to-zero · $0 cost from $900 GCP credit
> **🔐 Secrets:** ANTHROPIC_API_KEY wired via Secret Manager (revision `er-triage-v2-00004-xqq`)
> **📅 Status:** v2 deployed 2026-05-07. Triage assessment + RAG retrieval + memory persistence + Ragas eval all live.

---

## v1 → v2 — what changed (the diff Dinesh's scorecard implicitly asked for)

| Station | v1 (interview demo, scored 3.5) | v2 (this build, deployed) | Evidence file |
|---------|-------------------------------|---------------------------|---------------|
| **1 Deployment** | local Streamlit only | **Cloud Run + Docker + Artifact Registry** | `Dockerfile`, `deploy/cloudrun.sh`, live URL above |
| **5 Vector DBs** | discussed, not built | **Chroma persistent collection, 23 cases indexed** | `app/retrieval/store.py`, `outputs/embeddings/chroma.db/` |
| **6 Embeddings** | discussed, not visible | **Vertex AI `gemini-embedding-001` (3072-dim) + cache** | `app/retrieval/embed.py`, `outputs/embeddings/cache.json` |
| **7 Data Extraction** | synthetic only (Dinesh-approved scope) | **synthetic + 3 cases extracted from real Kaggle PDF** | `scripts/gen_past_cases.py`, `inputs/past_cases/er2_kaggle_source.pdf` |
| **8 Memory** | discussion-only | **Firestore session log, persists across scale-to-zero** | `app/memory.py` |

The 4 stations already at 4.0 (Eval, LLMs, Frameworks, Alignment) are preserved and still pass.

---

Each file annotated with which station on Dinesh's 9-station scorecard it directly satisfies.

Stations: 1=Deployment · 2=Evaluation · 3=LLMs (Thinking Core) · 4=Frameworks/Orchestration
          5=Vector Databases · 6=Embedding Models · 7=Data Extraction · 8=Memory · 9=Alignment & Observability

```
ER2/
│
├── app/                               ← runtime core (all stations live here)
│   │
│   ├── engine.py                      # [3: LLMs] [4: Frameworks/Orchestration]
│   │                                  #   main loop: patient → prompt → Claude API → JSON assessment
│   │                                  #   injects RAG context, ed_state, guidelines into every call
│   │
│   ├── prompt.py                      # [3: LLMs (Thinking Core)]
│   │                                  #   system prompt builder — XML-tagged context injection
│   │                                  #   forces Claude to cite rule IDs (R-ESI-T1..T5, R-ACS-01, etc.)
│   │                                  #   no hallucinated rules = eval passes rule_faithfulness 100%
│   │
│   ├── guardrails.py                  # [9: Alignment & Observability]
│   │                                  #   regex injection filter (jailbreak, ignore previous, etc.)
│   │                                  #   length cap 2000 chars on nurse note input
│   │                                  #   logs all trigger events → Cloud Logging via Python logging
│   │
│   ├── memory.py                      # [8: Memory]
│   │                                  #   Firestore session log — persists across Cloud Run scale-to-zero
│   │                                  #   log_case_review(), log_override(), get_session_stats()
│   │                                  #   graceful no-op when Firestore unavailable (local dev)
│   │
│   ├── streamlit_app.py               # [1: Deployment] [4: Frameworks/Orchestration]
│   │                                  #   UI shell — renders triage assessment card
│   │                                  #   similar cases panel (RAG results visible to user)
│   │                                  #   override panel with reason capture + memory logging
│   │                                  #   session_id generated per browser session (uuid4)
│   │
│   └── retrieval/
│       │
│       ├── embed.py                   # [6: Embedding Models]
│       │                              #   calls Vertex AI gemini-embedding-001 (3072-dim)
│       │                              #   returns dense vector for any text input
│       │
│       ├── store.py                   # [5: Vector Databases]
│       │                              #   writes/reads Chroma persistent collection
│       │                              #   upsert with case_id as doc ID, metadata stored alongside
│       │
│       └── search.py                  # [5: Vector Databases] [6: Embedding Models]
│                                      #   embed query → cosine similarity → top-k past cases
│                                      #   returns case_id, esi_tier, outcome, score, summary
│
├── scripts/
│   │
│   ├── build_index.py                 # [5: Vector Databases] [6: Embedding Models]
│   │                                  #   one-time indexer: reads cases.json → embed each → upsert Chroma
│   │                                  #   SHA-256 cache in cache.json to skip unchanged cases
│   │
│   ├── eval.py                        # [2: Evaluation]
│   │                                  #   Ragas 0.4.3 — deterministic metrics, no LLM calls
│   │                                  #   rule_faithfulness: 100% (zero hallucinated rule IDs, n=12)
│   │                                  #   adversarial_escalation: 100% (no tier upgrades on injection)
│   │                                  #   immediate_constraint_rate: 95.8%
│   │                                  #   saves full report → outputs/eval_report.json
│   │
│   └── gen_past_cases.py              # [7: Data Extraction]
│                                      #   generates synthetic past cases corpus
│                                      #   extracts 3 cases from real medical PDF (pdfplumber)
│                                      #   structured output: vitals, chief complaint, ESI tier, outcome
│
├── inputs/
│   │
│   ├── past_cases/
│   │   ├── cases.json                 # [7: Data Extraction] [5: Vector Databases]
│   │   │                              #   23 cases — 20 synthetic + 3 from PDF (PDF-001/002/003)
│   │   │                              #   this is the RAG retrieval corpus
│   │   │
│   │   └── er2_kaggle_source.pdf      # [7: Data Extraction]
│   │                                  #   source PDF — real triage cases from Kaggle ED dataset
│   │                                  #   pdfplumber extracts text → structured into case schema
│   │
│   ├── guidelines.md                  # [3: LLMs (Thinking Core)]
│   │                                  #   ESI rule set injected verbatim into every prompt
│   │                                  #   R-ESI-T1..T5, R-ACS-01, R-TIME-ECG, etc.
│   │                                  #   Claude must cite these IDs or eval flags it
│   │
│   ├── patients.json                  # [7: Data Extraction]
│   │                                  #   input schema: age, sex, vitals, chief_complaint, nurse_note
│   │                                  #   ER-0042 through ER-0053 — 12 cases used in eval run
│   │
│   └── ed_state.json                  # [4: Frameworks/Orchestration]
│                                      #   real-time ED context: beds_available, wait_times, staff
│                                      #   injected into prompt so Claude knows current capacity
│
├── outputs/
│   │
│   ├── embeddings/
│   │   ├── chroma.db/                 # [5: Vector Databases]  ← gitignored (binary)
│   │   │                              #   persistent Chroma collection — rebuilt with: make build-index
│   │   │
│   │   └── cache.json                 # [6: Embedding Models]
│   │                                  #   SHA-256 hash → embedding cache
│   │                                  #   prevents re-calling Vertex API for unchanged cases
│   │
│   ├── assessments/
│   │   └── ER-004*.json               # [3: LLMs (Thinking Core)] [2: Evaluation]
│   │                                  #   one JSON per patient: tier, rationale, cited_rules, similar_cases
│   │                                  #   similar_cases stored here — what RAG surfaced for that case
│   │
│   └── eval_report.json               # [2: Evaluation]
│                                      #   full Ragas output — metric scores + per-case breakdown
│                                      #   what the UI footer numbers come from
│
├── deploy/
│   └── cloudrun.sh                    # [1: Deployment]
│                                      #   gcloud run deploy — region us-west1, image from Artifact Registry
│
├── Dockerfile                         # [1: Deployment]
│                                      #   python:3.12-slim base
│                                      #   uses requirements-deploy.txt (no ragas — keeps image lean)
│
├── requirements-deploy.txt            # [1: Deployment]
│                                      #   prod deps only — ragas excluded (eval-only, never runtime)
│
├── requirements.txt                   # all stations — full local dev + eval deps
│
├── DASHBOARD.md                       # [4: Frameworks/Orchestration]
│                                      #   UI layout spec — exactly what renders in the demo
│
├── README.md                          # public-facing — live URL, quickstart, architecture diagram
├── pitch.md                           # CTO/CFO pitch deck (slide format)
└── Makefile                           # dev shortcuts: make run, make eval, make build-index
```

---

## Station → file quick-ref

| Station | Score | Key files |
|---------|-------|-----------|
| 1 Deployment | 3.5 ❌→✅ | `Dockerfile`, `deploy/cloudrun.sh`, `requirements-deploy.txt`, `app/streamlit_app.py` |
| 2 Evaluation | 4.0 ✅ | `scripts/eval.py`, `outputs/eval_report.json`, `outputs/assessments/` |
| 3 LLMs (Thinking Core) | 4.0 ✅ | `app/engine.py`, `app/prompt.py`, `inputs/guidelines.md`, `outputs/assessments/` |
| 4 Frameworks/Orchestration | 4.0 ✅ | `app/engine.py`, `app/streamlit_app.py`, `inputs/ed_state.json`, `DASHBOARD.md` |
| 5 Vector Databases | 3.5 ❌→✅ | `app/retrieval/store.py`, `app/retrieval/search.py`, `scripts/build_index.py` |
| 6 Embedding Models | 3.5 ❌→✅ | `app/retrieval/embed.py`, `app/retrieval/search.py`, `scripts/build_index.py`, `outputs/embeddings/cache.json` |
| 7 Data Extraction | 3.5 ❌→✅ | `scripts/gen_past_cases.py`, `inputs/past_cases/cases.json`, `inputs/patients.json`, `inputs/past_cases/er2_kaggle_source.pdf` |
| 8 Memory | 3.5 ❌→✅ | `app/memory.py` |
| 9 Alignment & Observability | 4.0 ✅ | `app/guardrails.py` |
