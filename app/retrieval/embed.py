"""Embedding wrapper — three backends with auto-fallback.

Backend priority (auto):
    1. vertex — Vertex AI gemini-embedding-001 (3072 dim, charges GCP credit)
                Requires `gcloud auth application-default login`.
    2. gemini — Google AI Studio gemini-embedding-001 (3072 dim, GEMINI_API_KEY)
                No ADC needed, same model quality, separate billing.
    3. local  — sentence-transformers/all-MiniLM-L6-v2 (384 dim, free, offline)
                Fallback when no API key — quality is meaningfully lower.

Switch explicitly with env var:
    EMBED_BACKEND=vertex|gemini|local   → force a specific backend
    (unset)                             → auto-detect in priority order

Cache: SHA256(text)[:16] → vector, persisted to outputs/embeddings/cache.json
NOTE: cache key includes backend name — switching backend forces re-embedding.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterable

CACHE_PATH = Path(__file__).parent.parent.parent / "outputs" / "embeddings" / "cache.json"
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

PROJECT = os.environ.get("GCP_PROJECT_ID", "maps-platform-20251011-140544")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
VERTEX_MODEL = "gemini-embedding-001"
LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_cache: dict[str, list[float]] | None = None
_backend: str | None = None
_local_model = None
_vertex_model = None
_gemini_ready = False


def _load_cache() -> dict[str, list[float]]:
    global _cache
    if _cache is not None:
        return _cache
    if CACHE_PATH.exists():
        with CACHE_PATH.open() as f:
            _cache = json.load(f)
    else:
        _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    with CACHE_PATH.open("w") as f:
        json.dump(_cache, f)


def _key(text: str, backend: str) -> str:
    return f"{backend}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def _try_vertex():
    global _vertex_model
    if _vertex_model is not None:
        return _vertex_model
    try:
        from google.cloud import aiplatform
        from vertexai.language_models import TextEmbeddingModel

        aiplatform.init(project=PROJECT, location=LOCATION)
        m = TextEmbeddingModel.from_pretrained(VERTEX_MODEL)
        _ = m.get_embeddings(["ping"])
        _vertex_model = m
        return m
    except Exception as e:
        print(f"[embed] Vertex unavailable ({type(e).__name__}: {str(e)[:80]}); using local fallback", file=sys.stderr)
        return None


def _try_gemini() -> bool:
    """Configure google-generativeai once. Returns True if usable."""
    global _gemini_ready
    if _gemini_ready:
        return True
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # smoke test
        _ = genai.embed_content(model="models/gemini-embedding-001", content="ping")
        _gemini_ready = True
        return True
    except Exception as e:
        print(f"[embed] Gemini unavailable ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
        return False


def _local():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(LOCAL_MODEL)
    return _local_model


def _resolve_backend() -> str:
    global _backend
    if _backend is not None:
        return _backend
    forced = os.environ.get("EMBED_BACKEND", "").lower()
    if forced == "vertex":
        if _try_vertex() is None:
            print("[embed] EMBED_BACKEND=vertex requested but unavailable", file=sys.stderr)
            sys.exit(1)
        _backend = "vertex"
    elif forced == "gemini":
        if not _try_gemini():
            print("[embed] EMBED_BACKEND=gemini requested but unavailable", file=sys.stderr)
            sys.exit(1)
        _backend = "gemini"
    elif forced == "local":
        _local()
        _backend = "local"
    else:
        # auto: vertex → gemini → local
        if _try_vertex() is not None:
            _backend = "vertex"
        elif _try_gemini():
            _backend = "gemini"
        else:
            _local()
            _backend = "local"
    print(f"[embed] backend = {_backend}", file=sys.stderr)
    return _backend


def embed_one(text: str) -> list[float]:
    return embed_many([text])[0]


def embed_many(texts: Iterable[str]) -> list[list[float]]:
    texts = list(texts)
    if not texts:
        return []
    backend = _resolve_backend()
    cache = _load_cache()
    out: list[list[float] | None] = [None] * len(texts)
    to_compute_idx: list[int] = []
    to_compute_texts: list[str] = []

    for i, t in enumerate(texts):
        k = _key(t, backend)
        if k in cache:
            out[i] = cache[k]
        else:
            to_compute_idx.append(i)
            to_compute_texts.append(t)

    if to_compute_texts:
        if backend == "vertex":
            m = _try_vertex()
            results = m.get_embeddings(to_compute_texts)
            vectors = [r.values for r in results]
        elif backend == "gemini":
            import google.generativeai as genai
            vectors = []
            for t in to_compute_texts:
                r = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=t,
                    task_type="retrieval_document",
                )
                vectors.append(r["embedding"])
        else:
            m = _local()
            vectors = m.encode(to_compute_texts, show_progress_bar=False).tolist()

        for idx, vec in zip(to_compute_idx, vectors):
            t = texts[idx]
            cache[_key(t, backend)] = vec
            out[idx] = vec
        _save_cache()

    return out  # type: ignore[return-value]


def dim() -> int:
    backend = _resolve_backend()
    if backend in ("vertex", "gemini"):
        return 3072
    return 384


if __name__ == "__main__":
    v = embed_one("chest pain 58F radiating to left arm")
    print(f"backend={_backend} dim={len(v)} sample={[round(x,3) for x in v[:5]]}")
