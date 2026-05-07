"""System prompt + tool schema for the triage engine."""

SYSTEM_PROMPT = """You are a decision-support assistant for emergency department triage. You do NOT make final triage decisions — clinicians do. You surface signals, organize next actions, and reduce cognitive load.

Rules you must follow:

1. Conservative bias: when uncertain between tiers, escalate (now > soon > wait).
2. Cite only rule_ids that exist in the provided guideline corpus. Never invent a rule_id.
3. Traffic-light convention for actions. Bucket fills only when its trigger condition is met — empty buckets stay empty.
   - 🔴 IMMEDIATE (max 3) — fires only if ANY of: vital red flag (hypotn/hypoxia/shock-tachy/peds-fever); life-threat hypothesis at HIGH confidence (ACS, stroke, SAH, anaphylaxis, sepsis); SLA already breached (door-to-ECG, door-to-CT). Otherwise leave empty.
   - 🟢 MONITOR (max 2) — fires when there is a pending workup (labs, imaging, vitals reassess). Almost always present except for trivial visit-and-discharge.
   - 🟡 ESCALATE OR REDIRECT (max 1) — fires only when ANY of: specialty decision needed (surgery / cardiology / neuro / psych); resource constraint (last monitored bed, RN/MD ratio breach); borderline tier where conservative bias bumped the call up. Otherwise leave empty.
4. Hard caps: immediate ≤ 3, monitor ≤ 2, escalate_or_redirect ≤ 1. Pick the highest-yield items only — this is an ER, the nurse acts on top items and moves on.
5. Every action carries a `reason` (one short sentence). Add `constraints_checked` for any clinical contraindication you verified (e.g., aspirin allergy, active GI bleed).
6. Read `ed_state` to populate the `constraints` block: bed/staff availability, on-call ETAs, time-target breaches.
7. Hypotheses must include rules_against entries when confidence is low — show your work.
8. Follow-up checklist items must each have an owner role (charge_nurse, rn, physician) and a deadline (now, <Nmin, ongoing, shift_end).
9. Review note: ALWAYS populate `review_note` to show the call is auditable, not blind. Include the tier chosen, the closest alternative considered, what specifically would downgrade (or upgrade) the call, and `subject_to_review: true`. This is the clinician transparency window — it renders right under the next-actions block, not at the bottom.
"""


TOOL_SCHEMA = {
    "name": "submit_assessment",
    "description": "Submit a triage assessment for one patient case. Must include all six panels.",
    "input_schema": {
        "type": "object",
        "required": ["urgency", "constraints", "hypotheses", "actions", "explanation", "checklist", "review_note"],
        "properties": {
            "urgency": {
                "type": "object",
                "required": ["tier", "confidence"],
                "properties": {
                    "tier":       {"enum": ["now", "soon", "wait"]},
                    "confidence": {"enum": ["high", "medium", "low"]},
                    "info_gaps":  {"type": "array", "items": {"type": "string"}},
                },
            },
            "constraints": {
                "type": "object",
                "properties": {
                    "resource": {"type": "array", "items": {"type": "object"}},
                    "time":     {"type": "array", "items": {"type": "object"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
            },
            "hypotheses": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "confidence"],
                    "properties": {
                        "name":               {"type": "string"},
                        "confidence":         {"enum": ["high", "medium", "low", "very_low"]},
                        "supporting_signals": {"type": "array", "items": {"type": "string"}},
                        "rules_against":      {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "actions": {
                "type": "object",
                "required": ["immediate", "monitor", "escalate_or_redirect"],
                "properties": {
                    "immediate":            {"type": "array", "maxItems": 3, "items": {"$ref": "#/$defs/action"}},
                    "monitor":              {"type": "array", "maxItems": 2, "items": {"$ref": "#/$defs/action"}},
                    "escalate_or_redirect": {"type": "array", "maxItems": 1, "items": {"$ref": "#/$defs/action"}},
                },
            },
            "explanation": {
                "type": "object",
                "required": ["summary", "citations"],
                "properties": {
                    "summary": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["rule_id", "signal"],
                            "properties": {
                                "rule_id": {"type": "string"},
                                "signal":  {"type": "string"},
                            },
                        },
                    },
                },
            },
            "checklist": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["task", "owner", "deadline"],
                    "properties": {
                        "task":     {"type": "string"},
                        "owner":    {"enum": ["charge_nurse", "rn", "physician", "specialist"]},
                        "deadline": {"type": "string"},
                        "status":   {"enum": ["pending", "done", "skipped"]},
                    },
                },
            },
            "review_note": {
                "type": "object",
                "required": ["tier_chosen", "subject_to_review"],
                "properties": {
                    "tier_chosen":         {"enum": ["now", "soon", "wait"]},
                    "alternative_tier":    {"enum": ["now", "soon", "wait"]},
                    "confidence_in_call":  {"enum": ["high", "medium", "low"]},
                    "why_this_tier":       {"type": "array", "items": {"type": "string"}},
                    "would_downgrade_if":  {"type": "array", "items": {"type": "string"}},
                    "would_upgrade_if":    {"type": "array", "items": {"type": "string"}},
                    "subject_to_review":   {"type": "boolean"},
                },
            },
        },
        "$defs": {
            "action": {
                "type": "object",
                "required": ["emoji", "action", "reason"],
                "properties": {
                    "emoji":  {"enum": ["🔴", "🟡", "🟢"]},
                    "action": {"type": "string"},
                    "reason": {"type": "string"},
                    "constraints_checked": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["check", "result"],
                            "properties": {
                                "check":  {"type": "string"},
                                "result": {"type": "string"},
                                "source": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}


def similar_cases_block(matches):
    lines = ["<similar_past_cases>"]
    for i, m in enumerate(matches, 1):
        meta = m.get("metadata", {})
        lines.append(f'  <case rank="{i}" similarity="{m.get("similarity", 0):.3f}">')
        lines.append(f'    <case_id>{meta.get("case_id", m.get("case_id", "?"))}</case_id>')
        lines.append(f'    <esi_tier>{meta.get("esi_tier", "?")}</esi_tier>')
        lines.append(f'    <outcome>{meta.get("outcome", "?")}</outcome>')
        lines.append(f'    <summary>{str(m.get("document", meta.get("summary", "")))[:300]}</summary>')
        lines.append("  </case>")
    lines.append("</similar_past_cases>")
    return "\n".join(lines)


def user_prompt(patient, ed_state, guidelines, similar_cases=None):
    import json
    rag_block = ""
    if similar_cases:
        rag_block = (
            "\n\n" + similar_cases_block(similar_cases) +
            "\n\nThe similar past cases above are retrieved from historical ED records. "
            "Use them as soft evidence — they inform pattern recognition but do not override clinical judgment or guideline rules."
        )
    return f"""<patient_case>
{json.dumps(patient, indent=2)}
</patient_case>

<ed_state>
{json.dumps(ed_state, indent=2)}
</ed_state>

<guidelines>
{guidelines}
</guidelines>{rag_block}

Produce a triage assessment for this patient. Use the submit_assessment tool. All six panels required."""
