# ADR-003: Chroma over managed vector DB (pgvector / Pinecone / Weaviate)

**Status:** Accepted
**Date:** 2026-05-07
**Deciders:** Anix Lynch

## Context

The retrieval pipeline needs a vector store for the past-case corpus. Today the corpus is 23 cases (3072-dim vectors). Reasonable forecasts for this artifact stay under 1k cases. The vector store needs to:

- Persist to disk between Cloud Run scale-to-zero events (or be regenerable cheaply).
- Be embeddable inside the Streamlit container (no separate service to manage).
- Support cosine similarity top-k (no need for hybrid search, filters, or reranking layer at the store level — `app/retrieval/search.py` handles those).
- Cost ~$0 at this scale.

## Decision

Use **Chroma** with persistent collection at `outputs/embeddings/chroma.db/`. Single-node, embedded, file-based.

## Consequences

### Positive

- **Zero ops.** No separate service, no auth, no quota to manage. The DB is just a directory on disk.
- **Free.** No managed-vector-DB monthly bill. Cloud Run idles at $0.
- **Container-shippable.** The chroma.db directory rebuilds via `scripts/build_index.py` on every container build, so the deployed image carries a fresh, cache-warm index.
- **Cosine top-k is exactly what's needed.** Chroma defaults align with the use case.
- **Local dev = production.** Same library, same API, same persistence model.

### Negative

- **Single-node ceiling.** Above ~10k cases or sustained high QPS, Chroma single-node hits practical limits.
- **No managed backups, no replicas, no point-in-time recovery.** Acceptable because the index is fully regenerable from `inputs/past_cases/cases.json` plus the embedding cache.
- **No hybrid search built in.** Need to add BM25 + reranker manually if dense-only retrieval underperforms. Not currently a concern at n=23.

### Neutral

- **Index rebuild is fast.** 23 cases × 3072-dim × ~100ms per Vertex call ≈ 3 seconds, mostly cached after first run via `outputs/embeddings/cache.json`.

## Alternatives considered

### A. pgvector on Cloud SQL (rejected for v2, candidate for v3)

- Pro: scales further, gets ACID + backups + observability, integrates with existing SQL skills.
- Con: requires a Cloud SQL instance ($~$10/month minimum), connection pool, IAM wiring, schema migrations. Overkill for n=23.
- Verdict: revisit when corpus crosses ~5k cases or when SQL-side joins (patient ↔ case ↔ outcome) become the natural query shape.

### B. Pinecone managed (rejected)

- Pro: zero-ops at large scale, hosted infra.
- Con: external vendor, monthly bill, extra auth, doesn't consume the GCP credit.
- Verdict: only worth it at scale where Chroma single-node has actually broken — not now.

### C. Weaviate / Qdrant self-hosted (rejected)

- Pro: more features (hybrid, modules, GraphQL).
- Con: separate service to deploy, more ops surface than Chroma offers in return at this scale.

### D. Vertex AI Vector Search (Matching Engine) (rejected for v2)

- Pro: GCP-native, scales massively, consumes the GCP credit.
- Con: setup complexity disproportionate to corpus size; minimum index instance has a non-trivial monthly cost.
- Verdict: candidate for v3 if corpus + traffic justify it.

## When to revisit

Migrate off Chroma when **any** of these is true:

- Corpus >5k cases AND query latency p95 > 200ms.
- Need filtered search (ESI tier, date range, demographic) at scale — Chroma's metadata filtering is functional but not its strong suit.
- Need hybrid retrieval (dense + BM25) — easier to layer on pgvector or Vertex Vector Search.
- Productizing for a client where their infra team prefers a specific managed service.

## Migration path (when triggered)

`app/retrieval/store.py` is the single file to swap. Keep the same `upsert(case_id, vector, metadata)` and `query(vector, k)` contract. Tested via `tests/integration/test_retrieval.py` (mock vs real backend).

## Related

- `app/retrieval/store.py` — Chroma persistence layer.
- `app/retrieval/search.py` — query interface (vendor-agnostic).
- `scripts/build_index.py` — index rebuilder.
- `outputs/embeddings/chroma.db/` — gitignored binary, rebuilt on container build.
