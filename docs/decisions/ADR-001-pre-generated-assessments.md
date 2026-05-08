# ADR-001: Pre-generated assessments at runtime, not live LLM-on-click

**Status:** Accepted
**Date:** 2026-05-07
**Deciders:** Anix Lynch

## Context

The deployed Streamlit app could call Claude live on every click (one assessment per visitor click) or render pre-generated assessments committed as JSON artifacts. Each path optimizes different things, and the choice shapes the rest of the architecture.

Live-on-click optimizes for: novelty, ability to take in a fresh patient typed into the form, perceived "smartness."

Pre-generated optimizes for: reproducibility, auditability, predictable cost, deterministic eval.

The product is a **decision-support reference implementation** — not a clinical production triage system. Reviewers need to see the same output as the eval claims. A hiring manager clicking the demo at 11pm should see the same results as one clicking it at 9am.

## Decision

The runtime renders assessments from `outputs/assessments/{case_id}.json`. The `app/engine.py` loop that calls Claude is run **offline** during build (locally with API key), and the resulting JSONs are committed to the repo and shipped inside the container.

## Consequences

### Positive

- **Reproducibility.** Same patient → same assessment, every visitor, every click.
- **Auditability.** Every assessment is git-tracked. `git diff outputs/assessments/ER-0052.json` between two model snapshots shows exactly what shifted.
- **$0 LLM cost per visitor.** Cloud Run bill is just the Streamlit container.
- **Deterministic eval.** `outputs/eval_report.json` reflects exactly what the demo shows. No drift between published metrics and live behavior.
- **Demo never breaks because of a flaky upstream.** Anthropic rate-limited? The demo still works.

### Negative

- **Cannot react to a brand-new patient typed into the UI live.** Only the 12 committed cases produce real triage. The form is illustrative.
- **New cases require a redeploy.** Add a patient → run engine locally → commit JSONs → push → redeploy.
- **Looks "less impressive" to reviewers expecting live model magic.** Mitigated by explaining the choice in `README.md` and `case-study.md`.

### Neutral

- **Engine code stays exercised** because regenerating assessments is the standard workflow when prompt or model changes. The `engine.py` is not dead code; it's the build tool.

## Alternatives considered

### A. Live LLM on every click (rejected)

- Pro: handles arbitrary patients, "feels smart."
- Con: cost scales with traffic, output drift between visitors, eval results don't match live behavior, demo breaks if Anthropic is rate-limited.
- Verdict: wrong fit for a *demonstration* surface where reproducibility matters more than novelty.

### B. Hybrid — pre-generated for committed cases, live for new (rejected for v2, candidate for v3)

- Pro: best of both.
- Con: doubles the surface area, doubles the failure modes, doubles the auth complexity. For a one-and-done RAG demo, complexity isn't earning its keep.
- Verdict: defer until a customer engagement justifies the work.

### C. Live with aggressive caching (rejected)

- Pro: fresh patients work, repeat clicks cheap.
- Con: still drifts between visitors on edge cases, still depends on Anthropic uptime.
- Verdict: same fundamental issue as A; cache layer adds complexity without solving the determinism problem.

## When to revisit

Invert this decision (move to live-on-click or hybrid) when:

- Customer engagement requires arbitrary live patient input.
- Eval coverage is large enough (n=500+) that determinism is no longer a demo concern.
- Volume is high enough that cache hit rate makes live affordable.

## Related

- `app/engine.py` — the offline loop this decision keeps offline.
- `outputs/assessments/` — the committed artifacts produced by this decision.
- `docs/architecture.md` — full architecture doc with this decision in context.
