# Architecture

System design notes for ED Triage Decision Support v2. Read this for the *why* behind each component; the *what* lives in the README and the *how* lives in code.

## Goals (in priority order)

1. **Decision support, not decision** — every output is cited, every override is logged, no black-box autonomy on a clinical surface.
2. **Reproducible demo** — every reviewer sees identical output. The same patient produces the same triage assessment, every time.
3. **Auditable** — every assessment is a committed artifact (`outputs/assessments/*.json`) that can be diffed, replayed, and explained.
4. **Cheap at idle** — scale-to-zero, $0/month when nobody is looking, ~$0.40 per 1k requests when someone is.

## High-level architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         RUNTIME (Cloud Run)                          │
│                                                                      │
│   Browser ──▶ Streamlit (app/streamlit_app.py)  ◀── reads ─┐         │
│                       │                                    │         │
│                       │  pick patient                      │         │
│                       ▼                                    │         │
│              outputs/assessments/{case_id}.json  ◀─────────┤         │
│              outputs/eval_report.json                      │         │
│              inputs/{patients,ed_state,guidelines}         │         │
│                                                            │         │
│   Override action ──▶ Firestore session log ◀── memory.py ─┘         │
└──────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ (no LLM call at runtime)
                                    │
┌───────────────────────────────────┼──────────────────────────────────┐
│                    OFFLINE BUILD (run once / on-demand)              │
│                                                                      │
│   inputs/patients.json + inputs/ed_state.json + inputs/guidelines.md │
│                            +                                         │
│   inputs/past_cases/cases.json (RAG corpus, 23 cases)                │
│                            │                                         │
│                            ▼                                         │
│   scripts/build_index.py  ──▶  Vertex AI gemini-embedding-001        │
│                            │   3072-dim · cached by SHA-256          │
│                            ▼                                         │
│   outputs/embeddings/chroma.db/ (persistent vector store)            │
│                            │                                         │
│                            ▼                                         │
│   app/engine.py                                                      │
│     for each patient:                                                │
│       embed query → top-k similar past cases (RAG)                   │
│       prompt.py builds XML context                                   │
│       Claude (claude-sonnet-4-6) → JSON assessment                   │
│       guardrails.py filters/length-caps                              │
│     write outputs/assessments/{id}.json (committed artifact)         │
│                            │                                         │
│                            ▼                                         │
│   scripts/eval.py                                                    │
│     deterministic Ragas-style metrics over assessments               │
│     write outputs/eval_report.json                                   │
└──────────────────────────────────────────────────────────────────────┘
```

## Key architectural decisions

For the long-form decision logs see [`docs/decisions/`](decisions/). The headline choices:

1. **Pre-generated assessments at the runtime edge, not live LLM-on-click.** Reproducibility, auditability, $0 LLM cost per visitor. Trade-off: the deployed app can't react to a brand-new patient typed in the form — only the 12 committed cases. For a *decision-support* surface, this is the right trade. For a *production-triage-on-arrival* surface, the architecture would invert (live engine, async logging).
2. **Vertex AI for embeddings, Anthropic for generation.** Embeddings are cheaper at Vertex and the GCP service-account auth is cleaner inside Cloud Run (no API key to manage). Generation is offline + cached, so vendor switching cost is contained to `app/engine.py` and `app/prompt.py`.
3. **Chroma for the vector store.** Single-node, zero-ops, persists to disk, fast enough for 23 cases. For >100k cases this becomes pgvector or a managed vector DB; the upgrade is one file (`app/retrieval/store.py`).
4. **XML-tagged prompts with forced rule citation.** Every output must cite a rule_id from `inputs/guidelines.md`. The eval suite then verifies *zero hallucinated rule_ids* — which it does (100% rule_faithfulness across n=12).
5. **Override panel writes to Firestore, falls back to no-op locally.** The runtime never crashes if Firestore isn't reachable; it just stops persisting overrides. Useful for local dev + production resilience both.

## Component responsibilities

| Component | Responsibility | Substitutes if you re-architected |
|-----------|----------------|-----------------------------------|
| `app/streamlit_app.py` | UI shell, patient picker, override capture | FastAPI + React; Gradio; HTMX |
| `app/engine.py` | Offline build loop: patient → prompt → Claude → JSON | LangChain agent; raw SDK; LangGraph |
| `app/prompt.py` | XML-tagged system prompt builder + tool schema | Jinja templates in `configs/prompts/` |
| `app/retrieval/embed.py` | Vertex AI embedding wrapper, SHA-256 cache | OpenAI text-embedding-3; Voyage; Cohere embed |
| `app/retrieval/store.py` | Chroma persistent collection | pgvector; Pinecone; Weaviate; Qdrant |
| `app/retrieval/search.py` | Embed query → top-k cosine → rerank | + cross-encoder rerank for higher precision |
| `app/memory.py` | Firestore session log | DynamoDB; Postgres; Redis Streams |
| `app/guardrails.py` | Regex injection filter, length cap | NeMo Guardrails; Llama Guard; OpenAI Moderation |
| `scripts/eval.py` | Deterministic Ragas-style metrics | Promptfoo; LangSmith eval; custom |
| `inputs/guidelines.md` | ESI v4 rule corpus (cited verbatim) | Domain guidelines for any vertical |

## Failure modes + how the design addresses them

| Failure | Design response |
|---------|-----------------|
| **Hallucinated rule_id** | Eval flags it. 100% faithfulness achieved by forced-citation prompt + post-validate against `guidelines.md`. |
| **Adversarial input** (normal vitals masking emergency) | RAG retrieves prior similar cases (e.g., silent infarct precedents). Prompt anchors against the in-context reassurance bias. ER-0052/0053 both → `now` correctly. |
| **Prompt injection** | `guardrails.py` regex filter on nurse-note input. Length-cap at 2000 chars. |
| **Cloud Run cold start** | Streamlit + Chroma load adds ~5s on first request after scale-to-zero. Acceptable for a decision-support tool, not for sub-second user-facing inference. |
| **Firestore unavailable** | `memory.py` falls back to no-op. Runtime continues; overrides not persisted in that window. |
| **Vertex AI down** | Embedding cache (`outputs/embeddings/cache.json`) covers the 23 indexed cases. New patients won't be embeddable until Vertex returns; fallback to `GEMINI_API_KEY` if configured. |
| **Anthropic rate limit during build** | `engine.py` retries with exponential backoff. Build is offline, so latency is fine. |

## Scaling (when this design starts to bend)

| Scale axis | Where this design works | Where it breaks |
|------------|------------------------|-----------------|
| Past-case corpus | Up to ~10k cases on Chroma single-node | >100k → migrate to pgvector or Pinecone |
| Concurrent users | ~20 concurrent on 1 Cloud Run instance | >50 concurrent → bump max-instances or move to Cloud Run gen2 |
| Patient throughput | Demo grade (12 cases pre-generated) | Live triage → invert to live engine + async logging + circuit breaker |
| Per-call latency | OK for offline (build is async) | Live triage at p99 < 2s → speculative decoding + smaller model + cached prompt prefix |

## Compliance considerations (HIPAA-adjacent)

This is a **decision-support reference implementation**. Real PHI handling would require:

- BAA in place with Anthropic + Google Cloud (both available).
- Cloud Run with VPC-SC perimeter, encryption at rest (default), encryption in transit (default).
- Audit logs to a separate compartment with retention policy (Cloud Logging + BigQuery sink).
- Override capture immutability (Firestore field-level access control, append-only collection).
- Data egress controls (no PHI to embedding cache; cache stores hash + vector only).
- Identity: per-clinician auth → IAP or auth proxy in front of Cloud Run.

The current synthetic-data demo intentionally does not implement these so the artifact stays freely shareable. The architecture is BAA-compatible — the deltas are configuration, not redesign.
