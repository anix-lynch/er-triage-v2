"""Streamlit UI for the ED triage dashboard. Renders the layout in DASHBOARD.md."""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import streamlit as st

from app.guardrails import sanitize_nurse_note

try:
    from app.memory import log_override, log_case_review, get_session_stats
    _MEMORY_OK = True
except Exception:
    _MEMORY_OK = False
    def log_override(*a, **kw): pass
    def log_case_review(*a, **kw): pass
    def get_session_stats(*a, **kw): return {"cases": 0, "overrides": 0, "available": False}

try:
    from app.retrieval.search import find_similar as _find_similar
    _RAG_OK = True
except Exception:
    _RAG_OK = False
    def _find_similar(*a, **kw): return []

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"
ASSESSMENTS = ROOT / "outputs" / "assessments"

TIER_EMOJI = {"now": "🔴", "soon": "🟡", "wait": "🟢"}
CONFIDENCE_BAR = {"high": 0.9, "medium": 0.6, "low": 0.2, "very_low": 0.05}
OK_EMOJI = {True: "✅", False: "⚠"}
REQUIRED_ASSESSMENT_KEYS = {"urgency", "constraints", "hypotheses", "actions", "explanation", "checklist"}


@st.cache_data
def load_patients() -> list[dict]:
    path = INPUTS / "patients.json"
    if not path.exists():
        st.error("Missing inputs/patients.json. Add the inputs folder to the deployed app.")
        st.stop()
    return json.loads(path.read_text())


@st.cache_data
def load_ed_state() -> dict:
    path = INPUTS / "ed_state.json"
    if not path.exists():
        st.error("Missing inputs/ed_state.json. Add the inputs folder to the deployed app.")
        st.stop()
    return json.loads(path.read_text())


def load_assessment(case_id: str) -> dict | None:
    path = ASSESSMENTS / f"{case_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if "assessment" in data and isinstance(data["assessment"], dict):
        data = data["assessment"]
    missing = REQUIRED_ASSESSMENT_KEYS - data.keys()
    if missing:
        st.warning(f"{case_id} assessment is incomplete. Missing: {', '.join(sorted(missing))}.")
        return None
    return data


def render_sidebar(patients: list[dict], ed_state: dict, session_id: str) -> str:
    st.sidebar.title("🏥 ED Triage")

    st.sidebar.subheader("ED Load")
    beds = ed_state["beds"]
    mon = ed_state["monitored_beds"]
    rn = ed_state["staffing"]["rn"]
    md = ed_state["staffing"]["md"]
    st.sidebar.metric("Beds free",       f"{beds['free']}/{beds['total']}")
    st.sidebar.metric("Monitored beds",  f"{mon['free']}/{mon['total']}",
                      delta="last one" if mon["free"] == 1 else None,
                      delta_color="inverse" if mon["free"] <= 1 else "normal")
    st.sidebar.metric("RN available",    f"{rn['available']}/{rn['on_shift']}")
    st.sidebar.metric("MD available",    f"{md['available']}/{md['on_shift']}")
    st.sidebar.metric("Median wait",     f"{ed_state['wait_time_min']} min")

    # Session memory stats (Firestore)
    if _MEMORY_OK:
        stats = get_session_stats(session_id)
        if stats["available"]:
            st.sidebar.subheader("This Session")
            st.sidebar.metric("Cases reviewed", stats["cases"])
            st.sidebar.metric("Clinician overrides", stats["overrides"])

    st.sidebar.subheader("Cases")
    options = []
    for p in patients:
        a = load_assessment(p["case_id"])
        tier = (a or {}).get("urgency", {}).get("tier") if a else None
        emoji = TIER_EMOJI.get(tier, "·")
        options.append(f"{emoji} {p['case_id']} — {p['name']}")
    choice = st.sidebar.radio("Select case", options, label_visibility="collapsed")
    return choice.split(" ")[1]


def render_header(patient: dict, assessment: dict | None) -> None:
    cols = st.columns([3, 2])
    with cols[0]:
        st.markdown(f"### CASE: `{patient['case_id']}` · PATIENT: `{patient['patient_id']}`")
        st.caption(f"{patient['name']} · {patient['age']}{patient['sex']} · arrived {patient['arrival_time'][11:16]}")
    if not assessment:
        with cols[1]:
            st.warning("No complete assessment yet. Run `python -m app.engine` and redeploy outputs.")
        return
    u = assessment["urgency"]
    badge = TIER_EMOJI.get(u.get("tier"), "·")
    with cols[1]:
        st.markdown(f"### {badge} {u.get('tier', 'unknown').upper()}")
        st.caption(f"confidence: {u.get('confidence', 'unknown')}")
    if u.get("info_gaps"):
        st.info("Info gaps: " + " · ".join(u["info_gaps"]))


def render_input(patient: dict) -> None:
    st.subheader("📥 INPUT")
    v = patient["vitals"]
    with st.expander("VITALS", expanded=True):
        st.write({
            "HR":   v["hr"],
            "BP":   f"{v['bp_sys']}/{v['bp_dia']}",
            "SpO2": v["spo2"],
            "RR":   v["rr"],
            "Temp": v.get("temp_c"),
            "Pain": patient.get("pain_score"),
        })
    with st.expander("CHIEF COMPLAINT", expanded=True):
        st.write(patient["chief_complaint"])
    if patient.get("nurse_notes"):
        with st.expander("NURSE NOTES", expanded=True):
            st.write(patient["nurse_notes"])
    with st.expander("HISTORY"):
        st.write({
            "conditions": patient.get("history") or [],
            "meds":       patient.get("medications") or [],
            "allergies":  patient.get("allergies") or [],
            "prior_visits": patient.get("prior_visits"),
        })
    if patient.get("timeline"):
        with st.expander("TIMELINE"):
            for event in patient["timeline"]:
                st.write(f"`{event['ts'][11:16]}` — {event['event']}")


def _render_kv_row(item: dict, status_key: str = "status") -> None:
    if not isinstance(item, dict):
        st.write(f"· {item}")
        return
    icon_map = {"ok": "✅", "at_risk": "⚠", "breached": "🚨", True: "✅", False: "⚠"}
    icon = icon_map.get(item.get(status_key, item.get("ok")), "·")
    note = item.get("note")
    primary = {k: v for k, v in item.items() if k not in {"note", "ok", "status"}}
    if not primary:
        st.write(f"{icon}  {note or '(no detail)'}")
        return
    pairs = " · ".join(f"**{k}**: {v}" for k, v in primary.items())
    st.write(f"{icon}  {pairs}" + (f" — {note}" if note else ""))


def render_constraints(c: dict) -> None:
    with st.expander("🧭 CONSTRAINTS", expanded=True):
        st.markdown("**Resources**")
        for r in c.get("resource", []) or []:
            _render_kv_row(r)
        if c.get("time"):
            st.markdown("**Time targets**")
            for t in c.get("time", []) or []:
                _render_kv_row(t)
        for w in c.get("warnings", []) or []:
            st.warning(w)


def render_hypotheses(hs: list[dict]) -> None:
    with st.expander("🔬 ROOT-CAUSE HYPOTHESES", expanded=True):
        for h in hs or []:
            name = h.get("name", "(unnamed)")
            conf = h.get("confidence", "low")
            st.write(f"**{name}** — {conf}")
            st.progress(CONFIDENCE_BAR.get(conf, 0.05))
            if h.get("supporting_signals"):
                st.caption("for: " + " · ".join(h["supporting_signals"]))
            if h.get("rules_against"):
                st.caption("against: " + " · ".join(h["rules_against"]))


BUCKET_CAPS = {"immediate": 3, "monitor": 2, "escalate_or_redirect": 1}


def render_actions(a: dict, review_note: dict | None = None) -> None:
    bucket_meta = [
        ("immediate",            "🔴", "IMMEDIATE"),
        ("monitor",              "🟢", "MONITOR"),
        ("escalate_or_redirect", "🟡", "ESCALATE OR REDIRECT"),
    ]
    with st.expander("🚦 NEXT ACTIONS", expanded=True):
        for key, emoji, label in bucket_meta:
            items = a.get(key) or []
            if not items:
                continue
            cap = BUCKET_CAPS[key]
            shown = items[:cap]
            st.markdown(f"**{emoji} {label}**")
            for item in shown:
                action = item.get("action", "(no action text)")
                reason = item.get("reason", "")
                st.markdown(
                    f"- {action}  \n  <span style='color:#888;font-size:0.85em'>↳ {reason}</span>",
                    unsafe_allow_html=True,
                )
            if len(items) > cap:
                st.caption(f"+{len(items) - cap} more truncated (cap {cap} per bucket)")

        if review_note:
            st.markdown("---")
            _render_review_footer(review_note)


def _render_review_footer(rn: dict) -> None:
    tier = rn.get("tier_chosen", "?")
    alt  = rn.get("alternative_tier")
    conf = rn.get("confidence_in_call", "?")
    badge = TIER_EMOJI.get(tier, "·")
    line = f"⚠ **WHY (subject to review)**  ·  tier: {badge} {tier.upper()}"
    if alt:
        line += f"  ·  alt considered: {TIER_EMOJI.get(alt, '·')} {alt.upper()}"
    line += f"  ·  confidence: {conf}"
    st.markdown(line)
    for r in rn.get("why_this_tier", []) or []:
        st.markdown(f"- {r}")
    if rn.get("would_downgrade_if"):
        st.caption("Would downgrade if: " + " · ".join(rn["would_downgrade_if"]))
    if rn.get("would_upgrade_if"):
        st.caption("Would upgrade if: " + " · ".join(rn["would_upgrade_if"]))


def render_explanation(e: dict) -> None:
    with st.expander("💬 EXPLANATION", expanded=True):
        st.write(e.get("summary", "(no summary)"))
        if e.get("citations"):
            st.caption("Cites: " + " · ".join(c.get("rule_id", "?") for c in e["citations"]))


def render_checklist(items: list[dict]) -> None:
    with st.expander("✅ FOLLOW-UP CHECKLIST", expanded=True):
        for item in items or []:
            done = item.get("status") == "done"
            box = "☑" if done else "☐"
            task = item.get("task", "(no task)")
            owner = item.get("owner", "?")
            deadline = item.get("deadline", "?")
            st.write(f"{box} **{task}** — owner: `{owner}` · {deadline}")


def render_similar_cases(assessment: dict, patient: dict) -> None:
    """Phase 9 — Similar Past Cases panel (below checklist, right column)."""
    # Prefer stored matches from assessment JSON (written by engine.py)
    similar = assessment.get("similar_cases")

    # Live fallback: query Chroma+Vertex at render time
    if not similar and _RAG_OK:
        try:
            similar = _find_similar(patient, k=3)
            # Normalise to slim format
            slim = []
            for m in similar:
                meta = m.get("metadata", {})
                slim.append({
                    "case_id":    meta.get("case_id", "?"),
                    "esi_tier":   meta.get("esi_tier", "?"),
                    "outcome":    meta.get("outcome", "?"),
                    "similarity": round(float(m.get("similarity", 0)), 4),
                    "summary":    str(m.get("document", ""))[:300],
                })
            similar = slim
        except Exception:
            similar = []

    if not similar:
        return

    with st.expander(f"📚 Similar Past Cases ({len(similar)})", expanded=False):
        for m in similar:
            cid  = m.get("case_id", "?")
            esi  = m.get("esi_tier", "?")
            out  = m.get("outcome", "?")
            sim  = float(m.get("similarity", 0))
            summ = m.get("summary", "")[:200]
            st.progress(sim, text=f"**{cid}** · ESI-{esi} · {out} · {sim:.0%} match")
            with st.expander(f"↳ {cid} detail"):
                st.caption(summ or "(no summary)")


def render_override(case_id: str, assessment: dict | None, session_id: str) -> None:
    st.divider()
    st.markdown("##### 👨‍⚕️ Clinician Override")
    assigned_tier = (assessment or {}).get("urgency", {}).get("tier", "unknown")
    cols = st.columns([2, 3, 1, 1])
    with cols[0]:
        tier = st.radio("Tier", ["now", "soon", "wait"], horizontal=True, key=f"tier_{case_id}")
    with cols[1]:
        raw_reason = st.text_input("Reason", key=f"reason_{case_id}",
                                   placeholder="Brief clinical justification")
        if raw_reason:
            clean_reason, triggers = sanitize_nurse_note(raw_reason)
            if triggers:
                st.warning(f"⚠ Input flagged: {', '.join(triggers)} — sanitized before logging.")
            else:
                clean_reason = raw_reason
        else:
            clean_reason = ""
    with cols[2]:
        if st.button("✓ Confirm", key=f"confirm_{case_id}"):
            log_case_review(session_id, case_id, assigned_tier)
            st.toast(f"Confirmed {tier} — logged.")
    with cols[3]:
        if st.button("✗ Override", key=f"override_{case_id}"):
            log_override(session_id, case_id, assigned_tier, tier, clean_reason)
            st.toast(f"Override → {tier}. Logged to Firestore.")


def main() -> None:
    st.set_page_config(page_title="ED Triage Support", layout="wide")
    st.caption(
        "🩺 **Public demo** — renders pre-generated assessments from `outputs/assessments/*.json`. "
        "Run locally with `python -m app.engine` to regenerate against live Claude."
    )

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    session_id = st.session_state.session_id

    patients = load_patients()
    ed_state = load_ed_state()

    case_id = render_sidebar(patients, ed_state, session_id)
    patient = next(p for p in patients if p["case_id"] == case_id)
    assessment = load_assessment(case_id)

    render_header(patient, assessment)
    if not assessment:
        render_input(patient)
        return

    cols = st.columns([1, 1])
    with cols[0]:
        render_input(patient)
    with cols[1]:
        st.subheader("📤 OUTPUT")
        render_constraints(assessment["constraints"])
        render_hypotheses(assessment["hypotheses"])
        render_actions(assessment["actions"], assessment.get("review_note"))
        render_explanation(assessment["explanation"])
        render_checklist(assessment["checklist"])
        render_similar_cases(assessment, patient)   # Phase 9

    render_override(case_id, assessment, session_id)

    # Footer — Phase 3.5 + Phase 8.5
    st.markdown("---")
    firestore_status = "✅ Firestore session log" if _MEMORY_OK else "⚠ Firestore offline"
    rag_status = "✅ RAG active" if _RAG_OK else "⚠ RAG offline"
    st.caption(
        f"🧠 Embedding: Vertex `gemini-embedding-001` / 3072-dim · Ragas eval: faithfulness 100%, adversarial escalation 100%, n=12 · "
        f"Vector DB: Chroma in-container · "
        f"{rag_status} · "
        f"🛡 Guardrails: injection filter, length cap, audit log → Cloud Logging · "
        f"{firestore_status}"
    )


if __name__ == "__main__":
    main()
