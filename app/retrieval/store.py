"""Chroma persistent vector store for past ED triage cases.

Why Chroma: zero-ops, single-file persistence, ships in container.
Production swap: Vertex AI Vector Search (or pgvector on AlloyDB) when scale > 1M vectors.

Schema:
    collection: ed_past_cases
    ids:        case_id (e.g., "PC-001")
    documents:  one-line summary (chief complaint + key vitals + outcome)
    metadatas:  {age, sex, esi_tier, outcome, disposition, adversarial}
    embeddings: pre-computed by app/retrieval/embed.py (NOT Chroma's default embedder)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

DB_PATH = Path(__file__).parent.parent.parent / "outputs" / "embeddings" / "chroma.db"
COLLECTION = "ed_past_cases"

_client: chromadb.PersistentClient | None = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    DB_PATH.mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=str(DB_PATH))
    _collection = _client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def upsert_cases(cases: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
    if len(cases) != len(embeddings):
        raise ValueError(f"cases ({len(cases)}) != embeddings ({len(embeddings)})")
    coll = _get_collection()
    ids = [c["case_id"] for c in cases]
    documents = [c.get("summary") or _compose_summary(c) for c in cases]
    metadatas = [
        {
            "age": int(c.get("age", 0)),
            "sex": str(c.get("sex", "")),
            "esi_tier": int(c.get("esi_tier", 0)),
            "outcome": str(c.get("outcome", "")),
            "disposition": str(c.get("disposition", "")),
            "adversarial": bool(c.get("adversarial", False)),
        }
        for c in cases
    ]
    coll.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)


def query(query_embedding: list[float], k: int = 3) -> list[dict[str, Any]]:
    coll = _get_collection()
    res = coll.query(query_embeddings=[query_embedding], n_results=k)
    out: list[dict[str, Any]] = []
    for i in range(len(res["ids"][0])):
        out.append({
            "case_id": res["ids"][0][i],
            "document": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res["distances"][0][i],
            "similarity": 1.0 - res["distances"][0][i],
        })
    return out


def count() -> int:
    return _get_collection().count()


def _compose_summary(case: dict[str, Any]) -> str:
    return (
        f"{case.get('age','?')}{case.get('sex','?')} - {case.get('chief_complaint','?')} - "
        f"ESI {case.get('esi_tier','?')} - {case.get('outcome','?')}"
    )
