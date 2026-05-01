# Requirements — Emergency Department Triage Support Assistant

## 1. Problem Statement

An emergency department receives a continuous flow of patients with varying levels of urgency. During peak hours, clinicians must make fast triage decisions with incomplete information while balancing patient safety and limited resources (beds, staff). As volume increases, it becomes harder to consistently determine who needs immediate attention, who can safely wait, and what actions should happen next.

The hospital wants a **lightweight assistant** that supports triage decisions during high-volume periods, augmenting clinical judgment with structured guidance and context. The assistant **does not replace** clinician decision-making — it surfaces signals, organizes next actions, and reduces cognitive load.

## 2. Users

- **Primary:** ED triage nurses, charge nurses, ED physicians
- **Secondary:** Bed-management coordinators, ED administrators (for retrospective audit)

## 3. Inputs

The system accepts a **set of patient cases**. Each case may include any combination of:

| Type | Examples |
|------|----------|
| Structured data | Vitals (HR, BP, SpO2, temp, RR), arrival time, age, sex, chief complaint code, ESI level if pre-assigned |
| Free-text notes | Symptom description, nurse triage notes, EMS hand-off narrative |
| Historical context | Prior visits, known conditions, medications, allergies (from EHR if available) |
| Temporal updates | New vitals, lab results, or notes that arrive after initial intake |

**Inputs may be incomplete, inconsistent, or change over time.** The system must handle:
- Missing fields (no BP recorded yet)
- Conflicting data (note says "no chest pain", vitals show tachycardia)
- Late-arriving updates (case re-assessment when new vitals appear)

## 4. Outputs

For each patient case, the assistant produces four artifacts:

### 4.1 Triaged Assessment
- **Urgency tier:** `now` / `soon` / `wait` (mapped to ESI 1-2 / 3 / 4-5)
- **Confidence:** `high` / `medium` / `low`
- **Information gaps:** explicit list of missing data that would change the assessment (e.g., "no SpO2 recorded", "pain scale not documented")

### 4.2 Recommended Next Actions (Immediate / Monitor / Escalate or Redirect)
Three action buckets per case study. Traffic-light color = patient safety state:
- 🔴 **Immediate** — act now, patient unsafe (e.g., "12-lead ECG now", "place on monitor", "ASA 324mg")
- 🟢 **Monitor** — patient stable, observe (e.g., "recheck vitals q15min", "watch mental status")
- 🟡 **Escalate or Redirect** — handoff needed (e.g., "notify cardiology", "redirect to fast-track", "trauma activation")

Each action carries `{action, reason, constraints_checked[]}` so every recommendation is auditable.

### 4.3 Root-Cause Hypotheses (with confidence)
Differential list driving the actions. Each: `{name, confidence: high|medium|low|very_low, supporting_signals[], rules_against[]}`. Top hypothesis drives Immediate actions; low-confidence hypotheses drive cheap rule-out tests in Monitor.

### 4.4 Constraints
Resource and time limits the engine considered:
- **Resource:** beds_free, monitored_beds, RN, MD, consult availability
- **Time:** door-to-ECG, door-to-disposition targets
- **Warnings:** breached limits or near-breaches surfaced for charge nurse

### 4.5 Explanation
Brief clinician-readable rationale citing relevant clinical signals, triage guidance (ESI rule_ids), prior patterns, contextual factors. Every claim links to a specific input field or named guideline rule_id.

### 4.6 Follow-up Checklist
Actionable items per case study, each `{task, owner, deadline, status}`:
- Assign a bed
- Notify a clinician
- Request additional vitals or labs
- Flag for reassessment at time T
- Document handoff notes (SBAR)

## 5. Functional Requirements

| ID | Requirement |
|----|-------------|
| F1 | Accept a batch of patient cases (1..N) in a single request |
| F2 | Produce all four output artifacts per case |
| F3 | Re-assess a case when new information arrives (delta input) and surface what changed |
| F4 | Flag conflicting or anomalous inputs rather than silently resolving them |
| F5 | Allow clinician override + capture the override reason for audit |
| F6 | Provide a per-case audit trail (input snapshot, model version, output, timestamp) |
| F7 | Support partial input — never fail because a field is missing |

## 6. Non-Functional Requirements

| Area | Target |
|------|--------|
| Latency | p50 < 3s, p95 < 8s for a single case |
| Throughput | ≥ 50 concurrent cases during peak |
| Availability | 99.9% during ED operating hours (24/7) |
| Privacy | HIPAA-compliant; PHI never leaves the hospital VPC; audit logs encrypted at rest |
| Safety | Conservative bias — when uncertain, escalate urgency rather than down-triage |
| Explainability | 100% of outputs cite source signals; no "black-box" recommendations |
| Auditability | All inputs/outputs retained for ≥ 7 years (regulatory) |

## 7. Out of Scope

- Final triage decision authority (clinician always decides)
- Diagnosis or treatment planning beyond next-action suggestion
- Direct EHR write-back (read-only integration in v1)
- Pediatric-specific triage protocols (v2)
- Mass-casualty / disaster triage protocols (v2)

## 8. Success Metrics

- **Decision support quality:** ≥ 90% agreement with clinician final triage on retrospective sample
- **Safety:** zero confirmed under-triage cases (high-acuity miscategorized as low) attributable to assistant guidance
- **Adoption:** used in ≥ 70% of triage encounters during peak hours within 3 months of rollout
- **Time saved:** median triage decision time reduced by ≥ 20%
- **Clinician trust:** post-deployment survey ≥ 4/5 on "explanations were useful"

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Under-triage of subtle high-acuity case | Conservative escalation bias; mandatory clinician sign-off; continuous retrospective audit |
| Alert fatigue from over-escalation | Tune thresholds against historical data; track false-positive rate |
| Input drift (new vitals format, new note style) | Schema validation at boundary; log unparseable inputs for review |
| Hallucinated guideline citations | Restrict explanations to a curated guideline corpus; verify cited rule exists |
| Bias across demographics | Audit output distributions by age/sex/race quarterly; document mitigations |
| Over-reliance / deskilling | UI framing: "decision support", not "decision"; require clinician confirmation |

## 10. Open Questions

- Which triage scale is canonical here — ESI, CTAS, MTS? (assumed ESI in §4.1)
- EHR integration: Epic / Cerner / other? Read-only API available?
- Is real-time bed/staff availability data accessible as a signal?
- What guideline corpus is approved for citation (institutional protocols vs. national)?
- Does the hospital have a model-governance board that must approve outputs format?
