# ED Triage Support — Pitch (CTO/CFO)

> Honest pitch. Slide deck format. Only describes what the prototype actually shows on screen.
> Length: 5 min pitch + 10 min Q&A.

---

## SLIDE 0 — Cover

**ED Triage Support Assistant**
*Decision support, not decision.*

Cited rules, not opinions. Logged overrides, not a black box.

---

## SLIDE 1 — Why we built this

**Triage today depends on which nurse is at the desk.**

- Same chest pain walks in twice → two different acuity scores, two different waits.
- No paper trail of *why* a tier was assigned.
- No flag when a clock is about to be missed (door-to-ECG, last monitored bed).
- When something goes wrong, the chart doesn't show what the nurse considered or what she ruled out.

> **One sentence:** the first 10 minutes of an ED visit are the most consequential — and the least documented.

---

## SLIDE 2 — What the prototype shows you

**A second pair of eyes for the triage nurse. Cited. Logged. Overridable.**

Open the demo → patient ER-0042 / 58F chest pain. The screen shows, side by side:

**Left side — what came in:**
- Vitals, chief complaint, nurse notes, history, allergies, meds, prior visits, arrival timeline.
- A form to add a new vital, lab result, or note → re-runs the assessment.

**Right side — what the assistant gives back:**
- An urgency badge with a confidence level.
- A list of **info gaps** still missing (e.g., "ECG not done").
- A ranked list of **possible causes** with confidence bars (high → very low).
- **Next actions in three buckets:**
  - 🔴 do now
  - 🟢 keep watching
  - 🟡 escalate / redirect
  Every action has a one-line reason next to it.
- A short **explanation paragraph** that cites rule IDs (e.g., R-ACS-01) → each ID resolves to a printed guideline page.
- A **follow-up checklist** with owner + deadline.
- A **📝 review note** at the bottom: tier chosen, alternative considered, what would downgrade or upgrade the call.

**Below the columns — what the human does:**
- Confirm or override the tier.
- Override requires a reason → written to the audit log.

**Sidebar — what management sees:**
- Live ED load: beds free, monitored beds, RN/MD available, current wait.
- Case queue color-coded by **the model's** tier (not the queue file — traceable to the assessment).
- Audit panel: which model, which rule pack, when the assessment was generated.

**Three things this changes on the floor:**
1. Triage decisions become **consistent** — same case, same rules, every shift.
2. Triage decisions become **defensible** — every recommendation cites a rule, every override is logged.
3. The **clock breaches and bed shortages get flagged before they hurt** — the assistant sees the constraint, not just the patient.

---

## SLIDE 3 — Proof: it doesn't blindly trust either signal

We built two adversarial cases. Both correctly classified 🔴 NOW.

| Case | Vitals | Nurse note | Verdict | Why |
|------|--------|------------|---------|-----|
| **ER-0052** Walter, 64M | normal | "ashen, drowsy, *this is not him*" | 🔴 NOW · medium conf | altered mental status fires ESI-T2 regardless of vitals; amlodipine masks tachycardia |
| **ER-0053** Diana, 28F | shock (HR 142, SBP 88, SpO2 91, T 38.7) | "I feel fine, mom is overprotective" | 🔴 NOW · high conf | *"appearance is not a vital sign"* — never downgrade shock vitals on self-report |

**The asymmetry is by design:**
- Any concerning signal — vitals OR notes OR history — can **escalate** the tier.
- Reassurance from the patient or from normal-looking vitals can **never** down-triage.
- Conservative bias breaks ties. Surfaced in the review note so it's visible, not hidden.

---

## SLIDE 4 — How it works

```
inputs/                          app/                     outputs/
patients.json     ──┐
ed_state.json     ──┼──►   engine.py (Claude Opus 4.7) ──►  assessments/
guidelines.md     ──┘       · prompt-cached system+rules     {case_id}.json
                            · tool_use forces 6-panel JSON
                            · cites only real rule_ids

                            streamlit_app.py ◄─────────────────┘
                            · 2-column input/output layout
                            · sidebar reads tier from
                              assessment file (traceable)
```

- 12 patient cases loaded today (10 baseline + 2 adversarial)
- 18 named ESI v4 rule_ids the model is allowed to cite
- Generation cost per case: ~$0.02
- Per-case latency: 8-15 seconds

---

## SLIDE 5 — What we're asking for

**A 30-minute call with one charge nurse and one IT lead.**

- Pick one ED.
- Run in **shadow mode** (assistant generates, nurse decides as today, no integration into clinical workflow).
- 4-week observation period.
- We publish the disagreement rate against your senior clinicians' chart reviews.

You decide whether to keep it.

---

## TALKING POINTS

**1. Open with the demo, not the slide.**
> "I want to show you something on a screen first. This took 30 seconds to load."
*(Click into ER-0042. Don't talk over it. Let them read.)*

**2. Show the override row before the recommendation.**
> "Notice the buttons at the bottom — confirm or override. The nurse always decides. We're showing her cited rules in 2 seconds, that's all."

**3. Make them click one citation.**
> "Click R-ACS-01. That's a printed guideline with a page number. Every recommendation on this screen resolves to a rule like that. There's no 'the model said so'."

**4. Show the review note.**
> "Scroll to the bottom of the output. This is the model's tie-break — what it considered as the alternative, what would change the call. The nurse sees the reasoning, not just the conclusion."

**5. Walk the two adversarial cases.**
> "ER-0052: vitals look fine, nurse note says he looks gray. The system calls this NOW. ER-0053: vitals are shock, patient says she feels fine. Also NOW. The system never lets reassurance override a red flag — that's the safety property."

**6. Land on the audit panel.**
> "If something goes wrong six months from now, you can answer 'why did the assistant say that on March 14 at 14:34?' This is the panel that answers it."

**7. Close with the pilot.**
> "What I'm asking for is a 30-min call with one charge nurse and one IT lead. We'll pick one ED, run it in shadow mode for a few weeks, and you decide."

---

## ANTICIPATED OBJECTIONS

| Objection | One-line answer |
|---|---|
| "Is it making medical decisions?" | "No — the nurse decides. The screen shows cited rules + a ranking. Every override is logged." |
| "What if the assistant is wrong?" | "Same answer as any guideline tool — the nurse overrides, and it's logged. We publish the disagreement rate against your senior clinicians' chart reviews." |
| "Will it slow the nurses down?" | "It runs in 2 seconds. The nurse types the same vitals she'd type into Epic. The output is a checklist, not a wall of text." |
| "What about PHI?" | "PHI stays in your environment. We can deploy it in your VPC or on your hardware." |
| "We already have ESI in Epic." | "Epic gives you a number 1-5. This gives you the reasoning, the cited rules, the constraint flags, and the audit trail. It sits next to Epic, doesn't replace it." |
| "Is this AI?" | "Yes. But every output cites a printed rule. The clinician decides. The audit log proves it. The review note shows what would have changed the call." |
| "What if the model anchors on the wrong hypothesis?" | "Look at ER-0053. It listed 4 differentials with confidence bars and `rules_against` for each. The model shows its work — anchoring is visible to the clinician, not hidden." |

---

## ONE-LINE CLOSER

> **"Decision support, not decision. Cited rules, not opinions. Logged overrides, not a black box. Want to pick one ED and try it for 30 days?"**
