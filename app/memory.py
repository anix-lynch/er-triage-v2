"""Session memory via Firestore. Graceful no-op when Firestore is unavailable."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_COLLECTION = "session_memory"
_db = None
_available: bool | None = None


def _get_db():
    global _db, _available
    if _available is not None:
        return _db
    try:
        from google.cloud import firestore
        _db = firestore.Client()
        _available = True
        logger.info("Firestore connected (collection: %s)", _COLLECTION)
    except Exception as exc:
        logger.warning("Firestore unavailable: %s", exc)
        _db = None
        _available = False
    return _db


def log_case_review(session_id: str, case_id: str, assigned_tier: str) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.collection(_COLLECTION).add({
            "session_id":    session_id,
            "case_id":       case_id,
            "assigned_tier": assigned_tier,
            "override_tier": None,
            "reason":        None,
            "ts":            datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("Firestore write (log_case_review) failed: %s", exc)


def log_override(session_id: str, case_id: str, assigned_tier: str,
                 override_tier: str, reason: str) -> None:
    db = _get_db()
    if db is None:
        return
    try:
        db.collection(_COLLECTION).add({
            "session_id":    session_id,
            "case_id":       case_id,
            "assigned_tier": assigned_tier,
            "override_tier": override_tier,
            "reason":        reason,
            "ts":            datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("Firestore write (log_override) failed: %s", exc)


def get_session_stats(session_id: str) -> dict:
    db = _get_db()
    if db is None:
        return {"cases": 0, "overrides": 0, "available": False}
    try:
        docs = list(db.collection(_COLLECTION).where(
            "session_id", "==", session_id
        ).stream())
        records = [d.to_dict() for d in docs]
        overrides = [r for r in records if r.get("override_tier") and
                     r["override_tier"] != r.get("assigned_tier")]
        return {"cases": len(records), "overrides": len(overrides), "available": True}
    except Exception as exc:
        logger.warning("Firestore read (get_session_stats) failed: %s", exc)
        return {"cases": 0, "overrides": 0, "available": False}
