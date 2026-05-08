# ADR-005: Streamlit UI over FastAPI + React

**Status:** Accepted
**Date:** 2026-05-07
**Deciders:** Anix Lynch

## Context

The deployed surface needs a web UI for reviewers (hiring managers, technical interviewers, potential clients) to click through 12 cases, see triage assessments with cited rules, view similar past cases, and submit overrides.

Two architectural patterns were available:

1. **Single-process Streamlit app** — Python-only, server-rendered, fast to build, less control over polish.
2. **FastAPI backend + React frontend** — separate services, more control, more polish, more moving parts.

The product is a **decision-support reference implementation** built solo on a 2026-05-07 sprint. Build cost matters; team scaling does not.

## Decision

Use **Streamlit** as the runtime UI, deployed as a single container on Cloud Run.

## Consequences

### Positive

- **Single language, single process.** Python end-to-end. No frontend toolchain, no CORS, no API contract to version.
- **Build-fast.** ~380 lines in `app/streamlit_app.py` covers the entire UI surface. A FastAPI + React equivalent is 5-10× the LOC for a marginal polish gain on a demo.
- **Sidebar + main panel pattern is a natural fit** for a case-picker + assessment-detail layout.
- **Cloud Run-friendly.** Single port, single image, no need for nginx fronting a frontend bundle.
- **Pre-generated assessments (per ADR-001) reduce the UI's job to "render JSON" — no live state management complexity** that would justify React's component model.

### Negative

- **Less polish than a custom React UI.** Streamlit's component library is functional but not designer-grade.
- **Hot reload is server-rendered, not client-side.** Every interaction triggers a full re-render. Acceptable at this scale; would not be at a high-interactivity surface.
- **Limits on UX customization.** Specific micro-interactions (e.g., split panes that resize independently) are awkward in Streamlit, easy in React.

### Neutral

- **Vertical scaling via Streamlit on Cloud Run is fine for a demo.** Production traffic would justify a different stack regardless.

## Alternatives considered

### A. FastAPI backend + React frontend (rejected for v2)

- Pro: production-grade UX, designer-friendly, scales horizontally cleanly.
- Con: 5-10× the build cost. The polish does not change the *capability* claim of the artifact — only its surface gloss. Build-cost matters for a one-and-done RAG demo.
- Verdict: revisit only if a customer engagement requires production UX or if React-side skills are the specific signal being shown.

### B. Gradio (rejected)

- Pro: even faster to build than Streamlit for ML demos.
- Con: stronger "ML demo aesthetic" than Streamlit, which can read as too informal for clinical decision-support framing.

### C. HTMX + FastAPI (rejected)

- Pro: lightweight, no JS toolchain, more control than Streamlit.
- Con: marginal gain over Streamlit for the features needed; introduces template complexity Streamlit absorbs.

### D. Server-rendered Django with templates (rejected)

- Pro: full control, mature framework.
- Con: heavier than warranted for a single-purpose demo.

## When to revisit

Migrate off Streamlit when:

- Customer engagement requires designer-grade UX with real product polish.
- High-interactivity surface (drag-and-drop, real-time collaboration, animations) becomes core.
- The artifact moves from "decision support reference implementation" to "clinician-facing production tool."

## Migration path (when triggered)

The pre-generated assessments (`outputs/assessments/*.json`) are the API contract. A React frontend can read those JSONs directly (or via a thin FastAPI wrapper around `app/engine.py` for live cases). The data layer doesn't change; only the rendering layer does.

## Related

- `app/streamlit_app.py` — the UI shell.
- `docs/ui-spec.md` — UI layout reference (was `DASHBOARD.md` in earlier root layout).
- `docs/architecture.md` — full architecture in context.
