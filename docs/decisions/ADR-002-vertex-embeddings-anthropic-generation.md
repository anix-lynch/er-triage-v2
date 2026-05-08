# ADR-002: Vertex AI for embeddings, Anthropic for generation

**Status:** Accepted
**Date:** 2026-05-07
**Deciders:** Anix Lynch

## Context

The pipeline needs two model calls of different shapes:

1. **Embeddings** — a function call per past case (and per query) to produce a fixed-length vector. Latency-tolerant (offline build), high volume, simple I/O.
2. **Generation** — a single chat-style call producing structured JSON triage assessment. Latency-sensitive when run, low volume per build (12-23 calls), complex prompt + tool-use schema.

Vendors considered: Anthropic (Claude), OpenAI (GPT + text-embedding-3), Google (Gemini + Vertex AI gemini-embedding-001), Voyage (voyage-3 embeddings only), Cohere (embed-v3 + Command).

## Decision

- **Embeddings:** Vertex AI `gemini-embedding-001` (3072-dim).
- **Generation:** Anthropic `claude-sonnet-4-6` via the official SDK.

## Consequences

### Positive

- **Auth cleanliness inside Cloud Run.** Vertex calls authenticate via the Cloud Run service account — no API key to manage, no secret to rotate, no leak risk in logs.
- **Cost on the GCP credit.** Embeddings consume the $900 GCP credit at the billing-account level (`01BF27-7A90D2-EDD523`). Anthropic is billed separately (per ADR-001 the deployed app does not call Claude at runtime, so per-visitor cost is zero anyway).
- **Best-of-each:** Claude is the strongest fit for clinical reasoning + structured tool-use; gemini-embedding-001 is performant on dense semantic retrieval, well-suited to medical text.
- **Vendor-switch contained.** Embeddings live in `app/retrieval/embed.py` (one file). Generation lives in `app/engine.py` + `app/prompt.py`. Switching either is a single-file refactor.

### Negative

- **Two vendors, two billing accounts, two auth setups.** More moving parts than a single-vendor pipeline.
- **`AnthropicVertex` is a viable alternative** that would unify auth (Claude on Vertex Model Garden, gcloud-default auth, $900 credit consumes it). Not adopted because the SDK shape and feature parity weren't fully verified at v2 ship time.

### Neutral

- **Embedding cache (`outputs/embeddings/cache.json`)** is keyed by SHA-256 of the input text — vendor-agnostic. Switching embedding vendors means invalidating the cache, not redesigning it.

## Alternatives considered

### A. OpenAI for both (rejected)

- Pro: single vendor, single key, smallest auth surface.
- Con: not aligned with Bchan's stack (GCP-preferred), doesn't consume the GCP credit, Claude is preferred for clinical reasoning quality.

### B. Anthropic for both via `AnthropicVertex` SDK (deferred)

- Pro: single vendor, GCP-billed, gcloud-default auth.
- Con: requires testing prompt-caching and tool-use parity vs the direct Anthropic SDK; not validated at v2 ship time. Strong candidate for v2.1 migration.

### C. Voyage embeddings + Anthropic generation (initial sketch in `deploy/cloudrun.sh`)

- Pro: Voyage is excellent on retrieval benchmarks for technical / domain text.
- Con: extra API key, extra Secret Manager entry, no GCP-billing path, doesn't consume the credit. The deploy script's stale `VOYAGE_API_KEY` reference (cleaned in commit `9657c0e`) was a relic of this evaluation phase.

### D. Cohere embed-v3 (rejected)

- Pro: high benchmark scores.
- Con: same multi-vendor cost as Voyage with no GCP-billing path.

## When to revisit

Migrate to single-vendor `AnthropicVertex` when:

- Tool-use + prompt-caching parity is verified for the use case.
- The auth simplification (one path, one role) outweighs the cognitive cost of changing.
- A v2.1 cycle is justified (e.g., scaling traffic, formalizing for client engagement).

## Related

- `app/retrieval/embed.py` — Vertex embedding call site.
- `app/engine.py` — Anthropic generation call site.
- `deploy/cloudrun.sh` — Secret Manager wiring for `ANTHROPIC_API_KEY`.
