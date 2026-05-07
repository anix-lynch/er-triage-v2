# DASHBOARD — ED Triage Support UI

Streamlit layout. Traffic-light convention: 🟢 safe · 🟡 caution · 🔴 urgent.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ ED Triage Support — Decision Support, not Decision     [Sync] [Admin] [Audit]     │
├──────────────┬────────────────────────────────────────────────────────────────────┤
│ SIDEBAR      │ CASE: ER-0042   PATIENT: P-9981   58F   arrived 14:22 (12 min ago) │
│              │ ┌──────────────────────────────────────────────────────────────┐   │
│ ED LOAD      │ │ URGENCY: 🔴 NOW    confidence: high    ESI 1-2               │   │
│  beds  4/12  │ │ Info gaps: ECG  ·  trop  ·  bilateral arm BP                 │   │
│  mon   1/4 ! │ └──────────────────────────────────────────────────────────────┘   │
│  RN    3/4   │                                                                    │
│  MD    1/2   │ ┌── 📥 INPUT ────────────┐ ┌── 📤 OUTPUT ──────────────────────┐   │
│  wait  38m   │ │ ▼ VITALS               │ │ ▼ CONSTRAINTS                     │   │
│              │ │   HR  118 !            │ │  beds_free      4/12     ok       │   │
│ CASES        │ │   BP  92/60 !          │ │  monitored      1/4     last      │   │
│ 🔴 ER-0042   │ │   SpO2 94              │ │  RN             3/4      ok       │   │
│ 🟡 ER-0043   │ │   RR  22               │ │  MD             1/2      ok       │   │
│ 🟢 ER-0044   │ │   T   37.1             │ │  cardiology   on-call 15m         │   │
│ 🟢 ER-0045   │ │                        │ │  door-to-ECG    12/10 BREACHED    │   │
│ 🟡 ER-0046   │ │ ▼ CHIEF COMPLAINT      │ │                                   │   │
│              │ │  "chest tightness 2h,  │ │ ▼ HYPOTHESES                      │   │
│ FILTERS      │ │   sweats, radiates to  │ │  ACS              high  ████████  │   │
│ [x] now      │ │   L jaw"               │ │  Aortic dissect.  low   █         │   │
│ [ ] soon     │ │                        │ │  PE               low   █         │   │
│ [ ] wait     │ │ ▼ NURSE NOTES          │ │  Anxiety/panic    v.low ·         │   │
│              │ │  diaphoretic, anxious, │ │                                   │   │
│ AUDIT        │ │  pain 7/10, no SOB     │ │ ▼ NEXT ACTIONS  (cap 3/2/1)       │   │
│  model:      │ │                        │ │  🔴 IMMEDIATE                     │   │
│  opus-4.7    │ │ ▼ HISTORY              │ │   • 12-lead ECG NOW               │   │
│  rules:      │ │  HTN, smoker           │ │     ↳ door-to-ECG breached        │   │
│  esi-v4      │ │  meds: lisinopril      │ │   • Cardiac monitor + IV access   │   │
│  generated:  │ │  allergies: NKDA       │ │     ↳ HR 118, SBP 92              │   │
│  14:34:02    │ │  prior visits: 2       │ │   • ASA 324mg chewable            │   │
│              │ │                        │ │     ↳ top hyp ACS, no contra      │   │
│ ACTIONS      │ │ ▼ TIMELINE             │ │  🟢 MONITOR                       │   │
│ [+ New]      │ │  14:22 arrival         │ │   • Reassess vitals q5min         │   │
│ [Reassess]   │ │  14:30 vitals          │ │   • Trop + d-dimer + BMP          │   │
│ [Copy SBAR]  │ │  14:33 nurse note      │ │  🟡 ESCALATE                      │   │
│ [Send]       │ │  14:34 → assessment    │ │   • Notify cardiology — standby   │   │
│              │ │                        │ │     ↳ high-conf ACS               │   │
│              │ │ ▶ ADD UPDATE           │ │  ─────────────────────────────    │   │
│              │ │  [+ vitals]            │ │  ⚠ WHY (subject to review)        │   │
│              │ │  [+ lab]               │ │   • ACS conf high (0.86)          │   │
│              │ │  [+ note]              │ │   • SBP 92 borderline             │   │
│              │ │  [Re-trigger]          │ │   • Last monitored bed → flag     │   │
│              │ │                        │ │                                   │   │
│              │ │                        │ │ ▼ EXPLANATION                     │   │
│              │ │                        │ │  Classic ACS pattern +            │   │
│              │ │                        │ │  hemodynamic instability →        │   │
│              │ │                        │ │  treat as ESI 1.                  │   │
│              │ │                        │ │  Cites: R-ACS-01,                 │   │
│              │ │                        │ │         R-VITALS-HYPOTN,          │   │
│              │ │                        │ │         R-ESI-T1                  │   │
│              │ │                        │ │                                   │   │
│              │ │                        │ │ ▼ FOLLOW-UP CHECKLIST             │   │
│              │ │                        │ │   ☐ Assign monitored bed          │   │
│              │ │                        │ │     charge_nurse · now            │   │
│              │ │                        │ │   ☐ Notify cardiology             │   │
│              │ │                        │ │     physician · now               │   │
│              │ │                        │ │   ☐ Trop + d-dimer + BMP          │   │
│              │ │                        │ │     rn · <10 min                  │   │
│              │ │                        │ │   [Copy SBAR] [Send]              │   │
│              │ └────────────────────────┘ └───────────────────────────────────┘   │
│              │                                                                    │
│              │ ┌── CLINICIAN OVERRIDE ──────────────────────────────────────┐     │
│              │ │ Tier: ( ) now ( ) soon ( ) wait   Reason: [_____________]  │     │
│              │ │ [Confirm]   [Override + log to audit trail]                │     │
│              │ └────────────────────────────────────────────────────────────┘     │
└──────────────┴────────────────────────────────────────────────────────────────────┘
```

## Next Actions — bucket trigger rules

The three buckets render only when their trigger condition is met. Empty buckets are hidden — no `(no items)` placeholder. The `WHY` footer is always shown.

| Bucket | Cap | Fires when ANY of |
|--------|-----|------------------|
| 🔴 IMMEDIATE | 3 | vital red flag (hypotn / hypoxia / shock-tachy / peds-fever) · life-threat hyp at HIGH conf (ACS, stroke, SAH, anaphylaxis, sepsis) · SLA already breached (door-to-ECG, door-to-CT) |
| 🟢 MONITOR   | 2 | pending workup (labs / imaging / vitals reassess). Almost always present. |
| 🟡 ESCALATE  | 1 | specialty decision needed (surgery / cardiology / neuro / psych) · resource constraint (last monitored bed, RN/MD ratio) · borderline tier where conservative bias bumped the call up |

## Bucket-by-tier examples

```
🟢 WAIT (P005 finger lac) — only Monitor
┌── ▼ NEXT ACTIONS ───────────────────────┐
│ 🟢 MONITOR                              │
│  • Clean + simple suture                │
│  • Tetanus booster (last >5y)           │
├─────────────────────────────────────────┤
│ ⚠ WHY (subject to review)               │
│  • Vitals normal, isolated minor injury │
│  • No red-flag history                  │
└─────────────────────────────────────────┘

🟡 SOON (P008 RLQ pain) — Monitor + Escalate, no Immediate
┌── ▼ NEXT ACTIONS ───────────────────────┐
│ 🟢 MONITOR                              │
│  • NPO + IV access                      │
│  • CBC + lipase + UA                    │
│                                         │
│ 🟡 ESCALATE                             │
│  • Notify surgery — possible appy       │
├─────────────────────────────────────────┤
│ ⚠ WHY (subject to review)               │
│  • RLQ + guarding + low fever           │
│  • Stable vitals — not 🔴 threshold     │
│  • Surgery decides operative vs observe │
└─────────────────────────────────────────┘

🔴 NOW (P001 chest pain) — all three
shown in the main dashboard above.
```

## Streamlit primitives

| Region | Primitive | Source |
|--------|-----------|--------|
| Sidebar (load / cases / filters / audit / actions) | `st.sidebar` | `inputs/ed_state.json` + scan of `inputs/patients.json` |
| Header strip (urgency badge, info gaps) | `st.container` + colored markdown | `assessment.urgency` |
| Two columns (input ┃ output) | `st.columns([1,1])` | — |
| Each `▼` section | `st.expander(expanded=True)` | corresponding JSON field |
| Hypothesis bars | `st.progress` (high=0.9 / med=0.6 / low=0.2 / very_low=0.05) | `assessment.hypotheses[].confidence` |
| Action buckets (🔴 / 🟢 / 🟡) | colored markdown blocks, capped 3/2/1 in code | `assessment.actions.*` |
| WHY footer | markdown block under the action buckets | `assessment.review_note` |
| Constraint table | row per constraint w/ status emoji | `assessment.constraints` |
| Add update form | `st.form` → appends to `case.updates[]` and re-triggers engine | user input |
| Override row | `st.radio` + `st.text_input` + buttons → audit log | user input |

## Project status

