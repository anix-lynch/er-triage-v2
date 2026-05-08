# Evaluation Methodology

How `outputs/eval_report.json` is produced and what each metric means. The full eval suite is `scripts/eval.py`; this doc explains the *why* behind every metric and the design choices around the eval harness.

## Eval philosophy

Two principles drive this eval:

1. **Deterministic where possible.** Most metrics here do not call an LLM. Rule_faithfulness, immediate_constraint_rate, and adversarial_escalation are pure string / structural checks. This means the eval can be run on every commit (CI) without API spend, and the numbers are stable across runs.
2. **Adversarial cases first-class.** Triage failure modes are not random — they are systematic. The two adversarial cases (ER-0052, ER-0053) are designed to tempt the model into under-triage via normal-looking vitals or patient reassurance. Eval scores them separately because they're the cases that matter most.

## Metric definitions

### `rule_faithfulness_pct`

**What it measures:** percentage of `rule_id` citations across all assessments that match a real entry in `inputs/guidelines.md`.

**Why it matters:** the prompt forces the model to cite rule_ids (R-ESI-T1..T5, R-ACS-01, R-TIME-ECG, etc.). A hallucinated rule_id is the most dangerous failure mode — it sounds clinical but is fabricated.

**How it's computed:**
1. Load all `outputs/assessments/*.json`.
2. Extract every `rule_id` from `cited_rules`.
3. Compare each against the rule_id list parsed from `inputs/guidelines.md`.
4. Score = (matching rule_ids / total rule_ids) × 100.

**Current result:** 100% (n=12). Zero fabricated rule_ids.

### `adversarial_escalation_pct`

**What it measures:** percentage of adversarial cases that are correctly escalated to `tier: now` (i.e., the model wasn't fooled).

**Why it matters:** a model that is "right on average" but misses adversarial presentations is unsafe. STEMI with normal vitals + patient reassurance kills.

**How it's computed:**
1. Load assessments for ER-0052 and ER-0053.
2. Check `tier == "now"` for both.
3. Score = (correctly escalated / total adversarial) × 100.

**Current result:** 100% (2/2). Both correctly tier `now` despite the trap.

### `immediate_constraint_pct`

**What it measures:** percentage of `tier: now` assessments where contraindication checks (`constraints_checked`) are populated.

**Why it matters:** an "escalate immediately" decision without checking what could go wrong (allergies, prior conditions, contraindicated meds) is sloppy. The model must surface what it considered, not just what it concluded.

**Current result:** 95.8% (n=12).

### `rag_context_rate_pct`

**What it measures:** percentage of assessments where `similar_cases` is stored in the output JSON.

**Note:** all 12 cases received RAG context at prompt time (verified in build logs). Only 2 of the 12 wrote `similar_cases` back into the assessment JSON — that's a *storage* gap, not a *retrieval* gap. Future versions will persist the retrieved similar_cases on every assessment for full audit trail.

**Current result:** 16.7% (2/12 stored). Read this with the caveat above.

### `median_confidence`

**What it measures:** distribution of self-reported confidence levels across assessments. The model reports `low | medium | high` per case.

**Why it matters:** a model that reports "high" on every adversarial case is overconfident and unsafe. The expected pattern is **high on clear cases, medium on adversarial-by-design cases.**

**Current result:** median **high**, with **medium** only on ER-0052 (the silent-MI presentation) — exactly the calibration we want.

## What this eval does NOT cover (limitations)

Stated honestly so reviewers don't have to ask:

- **No semantic similarity scoring of rationales.** A model could cite the right rule_ids with weak reasoning text. Adding a judge-LLM faithfulness score (Ragas `faithfulness`, `answer_relevance`) is the next step. Held off in v2 because adding a judge LLM makes eval non-deterministic and adds API spend per run.
- **n=12 is small.** Statistically, this is a smoke test, not a generalization claim. For production, n should be 500+ across a stratified sample (ESI-1 through ESI-5, with adversarial subsets).
- **No human comparison baseline.** A real eval would compare model triage against board-certified ED physician triage on the same cases. Held off because synthetic data + no PHI access in this demo.
- **Single model.** All assessments run through `claude-sonnet-4-6`. A real eval would compare across models (Claude / GPT / Gemini) and across prompt variants to understand cost/quality Pareto frontier.

## How to extend

If you want to add a new metric:

1. Edit `scripts/eval.py` — add a function that takes the assessment JSONs and returns a percentage / number.
2. Add the result to the dict written to `outputs/eval_report.json`.
3. Add a row to the README "Eval results" table.
4. (Optional) Wire to CI via `.github/workflows/ci.yml` so every PR re-runs.

If you want to add a new adversarial case:

1. Append a patient to `inputs/patients.json` (ER-0054 onward).
2. Run `python -m app.engine` to generate the assessment.
3. Add expected `tier` to the assertion list inside `scripts/eval.py`.
4. Re-run eval — the new case is now scored.

## Reproducing the published numbers

```bash
git clone https://github.com/anix-lynch/er-triage-v2 && cd er-triage-v2
pip install -r requirements.txt
python scripts/eval.py
cat outputs/eval_report.json
```

The eval is deterministic for the structural metrics. If a new model snapshot changes outputs, regenerate via `python -m app.engine` (requires `ANTHROPIC_API_KEY`) and re-eval.
