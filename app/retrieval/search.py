"""Similar-past-cases retrieval — the v2 hero feature.

Pipeline:
    current_case
        -> compose_query_text()
        -> embed.embed_one()
        -> store.query(k=N)
        -> tier-proximity rerank
        -> return top-3 with confidence band

Used by app/streamlit_app.py to render the "Similar Past Cases" sidebar panel.
"""

from __future__ import annotations

from typing import Any

from app.retrieval import embed, store


def compose_query_text(case: dict[str, Any]) -> str:
    parts = []
    if case.get("age") or case.get("sex"):
        parts.append(f"{case.get('age','?')}{case.get('sex','?')}")
    if case.get("chief_complaint"):
        parts.append(f"chief complaint: {case['chief_complaint']}")

    v = case.get("vitals") or {}
    abnormal = []
    if isinstance(v.get("HR"), (int, float)) and (v["HR"] > 100 or v["HR"] < 50):
        abnormal.append(f"HR {v['HR']}")
    if isinstance(v.get("SpO2"), (int, float)) and v["SpO2"] < 95:
        abnormal.append(f"SpO2 {v['SpO2']}")
    if isinstance(v.get("RR"), (int, float)) and (v["RR"] > 20 or v["RR"] < 10):
        abnormal.append(f"RR {v['RR']}")
    if isinstance(v.get("Pain"), (int, float)) and v["Pain"] >= 7:
        abnormal.append(f"pain {v['Pain']}/10")
    if v.get("BP") and isinstance(v["BP"], str):
        try:
            sys_bp = int(v["BP"].split("/")[0])
            if sys_bp < 100 or sys_bp > 160:
                abnormal.append(f"BP {v['BP']}")
        except (ValueError, IndexError):
            pass
    if abnormal:
        parts.append("abnormal vitals: " + ", ".join(abnormal))

    if case.get("nurse_note"):
        parts.append(f"note: {case['nurse_note']}")

    return " | ".join(parts)


def find_similar(
    case: dict[str, Any],
    k: int = 3,
    rerank_by_tier: int | None = None,
) -> list[dict[str, Any]]:
    query_text = compose_query_text(case)
    if not query_text:
        return []
    qvec = embed.embed_one(query_text)
    raw = store.query(qvec, k=max(k * 2, 6))

    if rerank_by_tier is not None:
        for r in raw:
            tier_delta = abs(int(r["metadata"].get("esi_tier", 0)) - rerank_by_tier)
            penalty = max(0, tier_delta - 2) * 0.15
            r["adjusted_similarity"] = r["similarity"] - penalty
        raw.sort(key=lambda r: r["adjusted_similarity"], reverse=True)
    else:
        raw.sort(key=lambda r: r["similarity"], reverse=True)

    return raw[:k]


if __name__ == "__main__":
    import json
    test_case = {
        "age": 58,
        "sex": "F",
        "chief_complaint": "chest tightness 2h, sweats, radiates to left jaw",
        "vitals": {"HR": 118, "BP": "92/60", "SpO2": 94, "RR": 22, "Temp": 37.1, "Pain": 7},
        "nurse_note": "diaphoretic, anxious, refuses to lie flat",
    }
    matches = find_similar(test_case, k=3)
    print(json.dumps(matches, indent=2, default=str))
