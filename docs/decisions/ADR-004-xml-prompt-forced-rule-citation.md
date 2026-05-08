# ADR-004: XML-tagged prompts with forced rule citation

**Status:** Accepted
**Date:** 2026-05-07
**Deciders:** Anix Lynch

## Context

The triage prompt needs to inject multiple kinds of context into the model:

- ESI guidelines (the rule corpus the model must cite)
- Current ED state (beds available, wait times, staff)
- Patient input (vitals, chief complaint, nurse note)
- Similar past cases retrieved by RAG (3 cases, with case_id + outcome)

Two prompt styles were considered:

1. **Flat prose** — "Here are the guidelines: ... Here is the patient: ... Please assess."
2. **XML-tagged sections** — `<guidelines>...</guidelines> <patient>...</patient> <similar_past_cases>...</similar_past_cases>`

Additionally, the output must be auditable. The model must cite specific rule_ids from the guidelines, and the eval suite must be able to verify those citations exist in the corpus.

## Decision

Two coupled choices:

1. **XML-tagged context injection.** Every section of the prompt is wrapped in semantic XML tags. Anthropic explicitly recommends this pattern for Claude.
2. **Forced rule citation in the output schema.** The tool-use schema requires the model to populate a `cited_rules` field with rule_id strings. The eval suite (`scripts/eval.py`) verifies every cited rule_id matches an entry in `inputs/guidelines.md`.

## Consequences

### Positive

- **Higher faithfulness.** XML tags give the model a clear signal about which span is which kind of context — no parsing ambiguity. Empirically, this reduces hallucinated cross-references.
- **Eval-as-gate.** `rule_faithfulness_pct` is computed by string-matching cited rule_ids against the guidelines corpus. Achieved 100% across n=12 — zero fabricated rule_ids.
- **The prompt design and the eval design reinforce each other.** Adding rule_faithfulness to the eval changed what the prompt forces the model to produce. Eval shapes the artifact.
- **Auditable output.** Every assessment JSON has `cited_rules: [R-ESI-T1, R-ACS-01, ...]`. A reviewer can trace each decision back to a specific guideline line.

### Negative

- **Output token cost goes up slightly** because the model is producing structured citation lists in addition to the assessment narrative. Marginal at this volume.
- **Prompt is more verbose** than a flat prose version. ~9KB system prompt in `app/prompt.py`. Acceptable trade for the determinism gain.
- **Tightly coupled to Claude.** Other models (GPT, Gemini) also do well with XML tagging, but this prompt is tuned specifically for Claude's behaviors.

### Neutral

- **The rule corpus (`inputs/guidelines.md`) becomes the source of truth.** Adding a rule means editing one file and re-running eval. No prompt changes needed; the model learns the new rule from the injected `<guidelines>` block.

## Alternatives considered

### A. Flat prose prompt (rejected)

- Pro: simpler to write.
- Con: Anthropic explicitly recommends XML tags for Claude; flat prose underperforms on multi-section inputs.

### B. JSON-formatted context blocks (rejected)

- Pro: structured.
- Con: Claude treats JSON-in-prompt as data to operate on, not always as instructions. XML tags map better to Claude's training signal for "this is context, that is task."

### C. No forced citation, free-form rationale (rejected)

- Pro: less structured, more "natural" output.
- Con: rule citations would drift, eval would need a judge LLM to verify (non-deterministic, cost), the failure mode of a hallucinated rule_id would not be reliably caught.

### D. Forced citation but verified via judge LLM (rejected)

- Pro: catches semantic drift, not just exact-match failures.
- Con: judge LLM is non-deterministic, adds API spend per eval run, and the failure mode we actually need to catch (fabricated rule_id) is structurally caught by exact-match.

## When to revisit

Add a judge-LLM faithfulness layer (Ragas `faithfulness`, `answer_relevance`) when:

- Eval corpus grows large enough (n=500+) that semantic drift becomes the bigger risk than fabrication.
- Production engagement justifies the per-run API spend.
- A v2.1 cycle adds Ragas's full metric suite.

## Related

- `app/prompt.py` — the XML-tagged system prompt builder.
- `inputs/guidelines.md` — rule corpus, source of truth for rule_ids.
- `scripts/eval.py` — `rule_faithfulness_pct` computation.
- `outputs/assessments/*.json` — `cited_rules` field per case.
- `docs/evaluation.md` — full eval methodology.
