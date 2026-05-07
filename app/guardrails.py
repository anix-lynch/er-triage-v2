"""Input sanitization and audit logging for the triage UI."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS = [
    r'ignore\s+(?:previous|prior|above|all)\b',
    r'forget\s+(?:everything|all|previous)\b',
    r'disregard\s+(?:previous|prior|above)\b',
    r'system\s*:',
    r'<\|im_start\|>',
    r'<\|im_end\|>',
    r'you\s+are\s+now\b',
    r'new\s+instruction',
    r'jailbreak',
    r'pretend\s+(?:you\s+are|to\s+be)\b',
    r'act\s+as\s+(?:if|a|an)\b',
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), flags=re.IGNORECASE)

MAX_LENGTH = 2000
MAX_CONTROL_CHARS = 10


def sanitize_nurse_note(text: str) -> tuple[str, list[str]]:
    """Strip injection patterns, cap length, remove control chars.

    Returns (cleaned_text, list_of_triggers_fired).
    Triggers are logged to Cloud Logging automatically via Python logging
    (Cloud Run streams stdout/stderr → Cloud Logging by default).
    """
    triggers: list[str] = []
    if not isinstance(text, str):
        return "", ["non-string-input"]

    ctrl_count = sum(1 for c in text if ord(c) < 32 and c not in "\n\r\t")
    if ctrl_count > MAX_CONTROL_CHARS:
        triggers.append("control-char-flood")
        text = "".join(c for c in text if ord(c) >= 32 or c in "\n\r\t")

    if len(text) > MAX_LENGTH:
        triggers.append("length-cap")
        text = text[:MAX_LENGTH]

    matches = _INJECTION_RE.findall(text)
    if matches:
        unique = sorted({m.strip().lower() for m in matches})
        triggers.append(f"injection-pattern({','.join(unique)})")
        text = _INJECTION_RE.sub("[REDACTED]", text)

    if triggers:
        logger.warning("guardrail fired | triggers=%s | text_len=%d", triggers, len(text))

    return text, triggers
