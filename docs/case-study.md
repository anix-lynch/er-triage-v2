# Case Study — ED Triage v2

A worked walkthrough of what was built, why, and what it demonstrates. Written for technical reviewers, hiring managers, and anyone evaluating whether the engineering matches the claims.

## Problem

Emergency Department triage nurses face a structural decision under time pressure: assign each arriving patient an Emergency Severity Index (ESI) tier (1 = immediate / 5 = non-urgent), choose immediate actions (ECG, IV access, isolation, etc.), and document rationale — all in roughly 60 seconds per patient on a busy shift.

Two failure modes dominate:

1. **Anchoring on normal-looking vitals.** Silent MI presents with normal HR/BP; STEMI can mask itself behind patient reassurance ("I'm fine, just a little chest discomfort"). Nurses are trained against this, but cognitive load + interruption density still produces under-triage.
2. **Citation gaps.** Tier decisions made under pressure are often documented after the fact; the *reasoning* is reconstructed, not captured live. This makes incident review harder and protocol drift invisible.

The hypothesis: an LLM-backed decision-support tool that retrieves similar past cases (RAG) and forces explicit rule-citation can reduce both failure modes — *as a second opinion*, not a substitute for the nurse.

## Approach

### Architecture choice: pre-generated assessments at the edge

The deployed Streamlit app does **not** call Claude at runtime. Instead, assessments for each patient are pre-generated offline (via `app/engine.py`) and committed as JSON artifacts (`outputs/assessments/{case_id}.json`). The runtime renders these.

This is a deliberate choice for a *decision-support reference implementation*:

- **Reproducibility** — every reviewer sees identical output. Critical for clinical demos where consistency builds trust.
- **Auditability** — every assessment is git-tracked. A reviewer can `git diff` two model snapshots and see exactly what changed.
- **Cost** — $0 in LLM spend per visitor.
- **Eval determinism** — the published Ragas-style eval numbers reflect *exactly* what the demo shows.

Trade-off: the demo cannot react to a brand-new patient typed live into the form. For a real production triage surface (where every arriving patient is novel), the architecture inverts: live engine, async logging, circuit breaker. The current architecture is the right fit for *demonstrating capability* — not for clinical production.

### RAG over 23 past cases

The retrieval pipeline:

```
patient   → Vertex AI gemini-embedding-001  (3072-dim)
          → Chroma cosine top-k
          → 3 most similar past cases injected as <similar_past_cases> XML
```

The 23-case corpus is 20 synthetic cases (across ESI 1–5) plus 3 cases extracted from a real public Kaggle ED dataset via `pdfplumber`. The PDF extraction shows the data-pipeline path; the synthetic cases give controlled coverage across tiers. Both sources land in the same `cases.json` schema so the retrieval is uniform.

### Forced rule citation + eval gate

Every prompt requires the model to cite `rule_id`s (R-ESI-T1..T5, R-ACS-01, R-TIME-ECG, etc.) from `inputs/guidelines.md`. The eval suite (`scripts/eval.py`) then:

1. Parses every cited rule_id from the assessments.
2. Verifies it exists in `guidelines.md`.
3. Reports `rule_faithfulness_pct`.

A hallucinated rule_id is the worst possible failure mode in clinical decision support — it sounds authoritative but is invented. By scoring this directly, we surface the failure mode that matters most.

### Adversarial cases as first-class

ER-0052 (Walter Brennan) and ER-0053 (Diana Chen) are designed to tempt under-triage:

- **ER-0052:** normal vitals + patient reassurance ("just chest discomfort") masking a silent MI.
- **ER-0053:** patient says "it's just anxiety," but SpO₂ is 89%.

These are scored separately because they're the cases where a "right on average" model is still dangerous.

## Result

| Metric | Result | What it means |
|--------|--------|---------------|
| `rule_faithfulness_pct` | **100%** | Zero hallucinated rule_ids across n=12 cases. |
| `adversarial_escalation_pct` | **100%** | Both ER-0052 and ER-0053 correctly tier `now`. |
| `immediate_constraint_pct` | 95.8% | Contraindication checks populated on almost all critical actions. |
| Median confidence | high | Calibrated — `medium` only on ER-0052 (the silent-MI presentation). |

Live demo: **https://er-triage-v2-tjb2srbb2q-uw.a.run.app**

Repo: **https://github.com/anix-lynch/er-triage-v2**

## What this demonstrates

The 9-station rubric this was built against (Deployment, Evaluation, LLMs, Frameworks/Orchestration, Vector DB, Embeddings, Data Extraction, Memory, Alignment & Observability) is now demonstrated in code:

- **Cloud deployment** — Cloud Run + Docker + Artifact Registry + Secret Manager
- **Eval-first design** — deterministic Ragas-style metrics committed as artifacts
- **LLM thinking core** — XML-tagged prompt with forced rule citation, Claude Sonnet 4.6
- **Orchestration** — engine.py loop, RAG injection, override capture, memory write
- **Vector DB** — Chroma persistent collection, 23 cases indexed
- **Embeddings** — Vertex AI gemini-embedding-001 (3072-dim) with SHA-256 cache
- **Data extraction** — pdfplumber pipeline from public Kaggle PDF → structured cases
- **Memory** — Firestore session log with graceful no-op fallback
- **Alignment & observability** — guardrails (regex injection filter, length cap), override logging

## Learnings worth naming

1. **Reproducibility beats novelty in decision support.** The first instinct is "live LLM on every click — fancier!" The right choice for a *demonstration of the capability* is reproducibility — every reviewer sees the same output. The fancy version is what you build *after* the demo earns the room.
2. **Eval as a gate, not as decoration.** Adding `rule_faithfulness_pct` to the eval suite changes the prompt design. Without it, "cite a rule" is a suggestion. With it, every assessment that fabricates a rule_id fails CI. Eval shapes the artifact.
3. **Adversarial cases catch real failure modes.** ER-0052 and ER-0053 are 16% of the test corpus but 100% of the safety-critical signal. A general aggregate score can pass with under-triage failures hidden inside it; per-adversarial-case scoring surfaces them.
4. **The architecture is one layer thicker than the prototype.** Moving from "Streamlit Cloud free demo" (v1) to Cloud Run + Firestore + Secret Manager + Artifact Registry (v2) is conceptually small but operationally meaningful. The image needs to be lean (no eval libs in prod), the secrets need to be mounted (not baked), the service account needs the right roles. Each one is mechanical; together they are the difference between a prototype and a deployable product.

## What I'd add next

If this becomes a real engagement rather than a demo:

1. **Larger eval corpus** (n=500+) stratified across ESI tiers, with held-out adversarial subsets.
2. **Model comparison.** Run the same prompts through Claude / GPT / Gemini, compare cost-per-correct-call. Build the Pareto chart.
3. **Live triage path.** Invert the architecture for production: live engine, async logging, circuit breaker. Pre-generated assessments become the test fixture.
4. **Auth + audit.** IAP in front of Cloud Run, per-clinician identity, append-only audit log to BigQuery.
5. **Document AI swap.** Replace `pdfplumber` with `documentai.googleapis.com` for layout-aware OCR on real clinical PDFs.

Each of these is one or two days of focused work. The architecture is BAA-compatible and ready for those upgrades — the deltas are configuration, not redesign.
