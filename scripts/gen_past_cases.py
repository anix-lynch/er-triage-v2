"""Generate 20 historical ED triage cases via Claude.

Routing: prefers Vertex Model Garden (charges GCP credit), falls back to direct
Anthropic API if Application Default Credentials are stale.

To enable Vertex routing (one-time):
    gcloud auth application-default login

Cost via direct Anthropic: ~$0.15 effective for 20 cases
Cost via Vertex Model Garden: ~$0 (eats GCP $900 credit)

Output: inputs/past_cases/cases.json with 20 ED triage cases
Run from ER2 root:  .venv/bin/python scripts/gen_past_cases.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


# Vertex region where Anthropic models live (per Vertex Model Garden docs)
REGION = "us-east5"
PROJECT = os.environ.get("GCP_PROJECT_ID", "maps-platform-20251011-140544")
VERTEX_MODEL = "claude-sonnet-4@20250514"
DIRECT_MODEL = "claude-sonnet-4-5-20250929"  # Sonnet 4.5 via direct API


def get_client_and_model():
    """Try Vertex Model Garden first; fall back to direct Anthropic API."""
    try:
        from anthropic import AnthropicVertex
        client = AnthropicVertex(region=REGION, project_id=PROJECT)
        # Smoke test auth
        _ = client.messages.create(
            model=VERTEX_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        print(f"[gen_past_cases] using Vertex Model Garden: {VERTEX_MODEL}")
        return client, VERTEX_MODEL
    except Exception as e:
        msg = str(e)
        print(f"[gen_past_cases] Vertex unavailable ({msg.split(chr(10))[0][:120]}); falling back to direct Anthropic")
        from anthropic import Anthropic
        if "ANTHROPIC_API_KEY" not in os.environ:
            print("[gen_past_cases] ERROR: ANTHROPIC_API_KEY not set. Run:", file=sys.stderr)
            print("  export ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY' ~/.config/secrets/global.env | cut -d'\"' -f2)", file=sys.stderr)
            sys.exit(1)
        client = Anthropic()
        print(f"[gen_past_cases] using direct Anthropic API: {DIRECT_MODEL}")
        return client, DIRECT_MODEL

OUTPUT = Path(__file__).parent.parent / "inputs" / "past_cases" / "cases.json"

PROMPT = """You are a clinical content generator. Produce 20 realistic but synthetic Emergency Department triage cases that span the full ESI (Emergency Severity Index) spectrum 1-5.

Requirements per case:
- Diverse chief complaints (chest pain, syncope, RLQ abdominal pain, headache, fever, lacerations, dyspnea, trauma, OB issues, psych, peds, geriatric).
- Realistic vitals (HR, BP, SpO2, RR, Temp, Pain 0-10).
- Nurse note (1-2 sentences, clinical voice, may include nuance like "anxious," "alert," "diaphoretic").
- ESI tier: 1 (resus), 2 (emergent), 3 (urgent), 4 (less urgent), 5 (non-urgent).
- Outcome: admitted | discharged | transferred | LWBS (left without being seen) | AMA.
- Disposition: ICU | floor | OBS | home | OR | psych_unit | trauma_bay.
- Include 3 ADVERSARIAL pairs:
  - Case where vitals look normal but nurse note signals red flag
  - Case where age masks severity (elderly with subtle sepsis)
  - Case where young/stable presents with rare condition

Distribution target:
- ESI 1: 2 cases
- ESI 2: 5 cases
- ESI 3: 7 cases
- ESI 4: 4 cases
- ESI 5: 2 cases

Return STRICT JSON only, no prose, no markdown fences. Schema per case:
{
  "case_id": "PC-001" through "PC-020",
  "age": int,
  "sex": "M" | "F",
  "chief_complaint": str,
  "vitals": {"HR": int, "BP": "sys/dia", "SpO2": int, "RR": int, "Temp": float, "Pain": int},
  "nurse_note": str,
  "history": str,
  "esi_tier": 1-5,
  "outcome": str,
  "disposition": str,
  "adversarial": bool,
  "summary": str  // one-line summary for embedding
}

Output: {"cases": [...]}.
"""


def main() -> None:
    client, model = get_client_and_model()
    print("[gen_past_cases] generating 20 cases...")
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        messages=[{"role": "user", "content": PROMPT}],
    )

    text = msg.content[0].text.strip()
    # Strip markdown fences if model adds them despite instructions
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:].lstrip("\n")
        text = text.rsplit("```", 1)[0].strip()

    data = json.loads(text)
    cases = data.get("cases", [])
    if not cases:
        print(f"[gen_past_cases] ERROR: no cases parsed. raw output:\n{text[:500]}", file=sys.stderr)
        sys.exit(1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as f:
        json.dump(
            {
                "_README": "20 historical ED triage cases — synthetic but clinically realistic. Generated via Claude Sonnet on Vertex Model Garden.",
                "_model": model,
                "_count": len(cases),
                "cases": cases,
            },
            f,
            indent=2,
        )
    print(f"[gen_past_cases] wrote {len(cases)} cases → {OUTPUT}")
    tiers = {}
    for c in cases:
        tiers[c["esi_tier"]] = tiers.get(c["esi_tier"], 0) + 1
    print(f"[gen_past_cases] ESI tier distribution: {dict(sorted(tiers.items()))}")
    adv = sum(1 for c in cases if c.get("adversarial"))
    print(f"[gen_past_cases] adversarial cases: {adv}")


if __name__ == "__main__":
    main()
