# ED Triage Guidelines (ESI v4)

Rule pack the engine is allowed to cite. Every `rule_id` here can appear in `assessment.explanation.citations[]`. No rule_id → no citation.

**Source:** ESI Implementation Handbook v4 (Agency for Healthcare Research and Quality, AHRQ).
**Tier convention:** ESI 1 = resuscitation · 2 = emergent · 3 = urgent · 4 = less urgent · 5 = non-urgent.

---

## ESI tier rules

### RULE R-ESI-T1: resuscitation
**Trigger:** requires immediate life-saving intervention (intubation, defibrillation, vasoactive drip, blood for hemorrhage, naloxone for apnea).
**Action class:** Immediate
**Tier:** ESI 1
**Source:** Handbook v4, ch. 3 p. 12.

### RULE R-ESI-T2: emergent / high-risk
**Trigger:** high-risk situation, OR confused/lethargic/disoriented, OR severe pain ≥7/10 with concerning vitals.
**Action class:** Immediate
**Tier:** ESI 2
**Source:** Handbook v4, ch. 3 p. 14.

### RULE R-ESI-T3: many resources
**Trigger:** stable vitals AND likely needs ≥2 resources (lab + imaging, IV fluids + meds, specialty consult + procedure).
**Action class:** Monitor
**Tier:** ESI 3
**Source:** Handbook v4, ch. 4 p. 18.

### RULE R-ESI-T4: one resource
**Trigger:** stable vitals AND likely needs 1 resource (single x-ray, simple suture, single med).
**Action class:** Monitor
**Tier:** ESI 4
**Source:** Handbook v4, ch. 4 p. 19.

### RULE R-ESI-T5: no resource
**Trigger:** stable vitals AND no resources expected (visual check, prescription refill, simple wound care).
**Action class:** Monitor
**Tier:** ESI 5
**Source:** Handbook v4, ch. 4 p. 20.

---

## Vital sign red flags

### RULE R-VITALS-HYPOTN: hypotension
**Trigger:** SBP < 100 mmHg in adult, OR SBP < age-specific threshold in peds.
**Action class:** Immediate (escalate tier by 1, minimum ESI 2)
**Source:** Handbook v4, appendix B.

### RULE R-VITALS-TACHY: tachycardia
**Trigger:** HR > 110 sustained in adult at rest, OR > 99th-percentile-for-age in peds.
**Action class:** Monitor (consider ESI 2 if combined with other red flags)
**Source:** Handbook v4, appendix B.

### RULE R-VITALS-HYPOXIA: hypoxia
**Trigger:** SpO2 < 92% on room air (adult or peds).
**Action class:** Immediate (minimum ESI 2)
**Source:** Handbook v4, appendix B.

### RULE R-VITALS-FEVER-PEDS: pediatric fever
**Trigger:** infant <3 mo with T ≥ 38.0°C, OR child with T ≥ 39.5°C plus toxic appearance.
**Action class:** Immediate (minimum ESI 2)
**Source:** Handbook v4, appendix C (pediatric).

---

## Disease-specific rules

### RULE R-ACS-01: acute coronary syndrome — chest pain
**Trigger:** chest pain or anginal-equivalent (jaw/arm pain, dyspnea, diaphoresis) AND any of: age ≥40, known CAD/HTN/DM/smoker, abnormal vitals.
**Action class:** Immediate — 12-lead ECG within 10 min of arrival; cardiac monitor; IV access; ASA 324mg chewable if no contraindication.
**Tier:** ESI 1-2
**Source:** ACC/AHA NSTEMI guideline 2014; door-to-ECG ≤10 min standard.

### RULE R-STROKE-01: acute stroke — focal neuro deficit
**Trigger:** sudden focal deficit (face droop, arm drift, slurred speech, vision loss, confusion) within 24h, especially within 4.5h last-known-well window.
**Action class:** Immediate — activate stroke team; CT head non-contrast STAT; NIHSS; finger-stick glucose; do NOT lower BP unless > 220/120 (or candidate for tPA).
**Tier:** ESI 1
**Source:** AHA/ASA acute ischemic stroke guideline 2019.

### RULE R-SAH-01: subarachnoid hemorrhage — thunderclap headache
**Trigger:** sudden severe headache "worst of life" reaching peak intensity within minutes, OR new headache with neck stiffness, vomiting, or altered mental status.
**Action class:** Immediate — CT head non-contrast STAT; if negative and high suspicion → LP for xanthochromia.
**Tier:** ESI 1-2
**Source:** AHA/ASA SAH guideline 2012.

### RULE R-ANAPH-01: anaphylaxis
**Trigger:** acute onset (minutes-hours) of skin/mucosal involvement PLUS any of: respiratory compromise, hypotension, persistent GI symptoms, AFTER exposure to known/likely allergen.
**Action class:** Immediate — IM epinephrine 0.3mg (adult) / 0.15mg (peds <30kg) anterolateral thigh; supine; IV fluids if hypotensive; H1+H2 blockers + steroids as adjunct.
**Tier:** ESI 1
**Source:** WAO anaphylaxis guideline 2020.

### RULE R-PEDS-RESP-01: pediatric respiratory distress
**Trigger:** child with RR > 99th-percentile-for-age, OR SpO2 < 92%, OR accessory muscle use, OR unable to speak full sentences.
**Action class:** Immediate — supplemental O2; albuterol nebulizer if wheezing; minimum ESI 2.
**Tier:** ESI 1-2
**Source:** AAP / PALS 2020.

### RULE R-HEAD-ANTICOAG-01: head trauma on anticoagulants
**Trigger:** any head injury (even minor, GCS 15) in patient on warfarin, DOAC (apixaban/rivaroxaban/dabigatran/edoxaban), or antiplatelet therapy.
**Action class:** Immediate — CT head non-contrast STAT regardless of GCS; check INR if on warfarin; observation ≥6h even if first CT negative.
**Tier:** ESI 2
**Source:** ACEP clinical policy on mild TBI 2008; updated DOAC literature.

### RULE R-SEPSIS-01: sepsis screen
**Trigger:** suspected/confirmed infection AND any 2 of: T <36 or >38°C, HR >90, RR >20, altered mental status, SBP <100.
**Action class:** Immediate — lactate, blood cultures x2 BEFORE antibiotics, broad-spectrum antibiotics within 1h, 30 mL/kg crystalloid if hypotensive or lactate ≥4.
**Tier:** ESI 1-2
**Source:** Surviving Sepsis Campaign 2021.

---

## Citation contract

The engine MUST:
1. Cite by `rule_id` only — never paraphrase a rule into the explanation.
2. Resolve every `citations[]` entry to a rule above. Unresolved citation = invalid output.
3. Combine rules additively (e.g., chest pain + hypotension = R-ACS-01 + R-VITALS-HYPOTN + R-ESI-T1).
