"""Build the Chroma vector index from inputs/past_cases/cases.json.

One-shot: reads past cases, embeds via app/retrieval/embed.py, upserts to Chroma.
Idempotent — Chroma upsert overwrites by id.

Run:  .venv/bin/python scripts/build_index.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make app/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.retrieval import embed, store

CASES_PATH = Path(__file__).parent.parent / "inputs" / "past_cases" / "cases.json"


def compose_doc(case: dict) -> str:
    """Compose document text used for both embedding and Chroma document storage."""
    parts = [
        f"{case.get('age','?')}{case.get('sex','?')}",
        f"chief complaint: {case.get('chief_complaint','')}",
    ]
    v = case.get("vitals") or {}
    if v:
        parts.append(
            f"vitals: HR {v.get('HR')} BP {v.get('BP')} SpO2 {v.get('SpO2')} RR {v.get('RR')} Temp {v.get('Temp')} Pain {v.get('Pain')}"
        )
    if case.get("nurse_note"):
        parts.append(f"nurse note: {case['nurse_note']}")
    if case.get("history"):
        parts.append(f"history: {case['history']}")
    parts.append(f"ESI tier {case.get('esi_tier','?')}, outcome: {case.get('outcome','?')}")
    return " | ".join(parts)


def main() -> None:
    with CASES_PATH.open() as f:
        data = json.load(f)
    cases = data.get("cases", [])
    if not cases:
        print(f"no cases in {CASES_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"[build_index] {len(cases)} cases loaded")

    # Compose document texts (used for both embedding input + Chroma doc storage)
    docs = [compose_doc(c) for c in cases]

    # Override summary with our composed doc so retrieval has rich context
    for c, d in zip(cases, docs):
        c["summary"] = d

    print(f"[build_index] embedding {len(docs)} cases...")
    vectors = embed.embed_many(docs)
    print(f"[build_index] embedded {len(vectors)} × {len(vectors[0])} dim")

    print("[build_index] upserting to Chroma...")
    store.upsert_cases(cases, vectors)
    print(f"[build_index] Chroma collection size: {store.count()}")


if __name__ == "__main__":
    main()
