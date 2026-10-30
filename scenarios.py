"""Unit 8 evaluation scenarios for the two criteria that require live /submit.

Criterion 1 requires ten ACTUAL human-authored samples from the writer.
Criterion 4 sends malformed HTTP JSON bodies.
Criteria 2, 3, and 5 are tested with controlled signal injection through
test_unit7_acceptance.py, including the POST /appeal route.

Do not invent or AI-generate human ground truth. Save ten original passages
privately as a JSON array at data/human_originals.private.json (gitignored),
or set PROVENANCE_HUMAN_CORPUS to the path of another JSON array.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGINALS = Path(os.getenv(
    "PROVENANCE_HUMAN_CORPUS",
    str(ROOT / "data" / "human_originals.private.json"),
))


def load_originals() -> list[str]:
    if not ORIGINALS.is_file():
        return []
    try:
        payload = json.loads(ORIGINALS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read genuine writing corpus: {exc}") from exc
    if not isinstance(payload, list) or any(not isinstance(t, str) for t in payload):
        raise ValueError("The authentic corpus must be a JSON array of strings.")
    return payload


SCENARIOS = [
    {
        "name": "verified human originals (private corpus, not AI-generated)",
        "criterion": 1,
        "texts": load_originals(),
    },
    {
        "name": "malformed JSON object submissions",
        "criterion": 4,
        # The [] case is also tested in test_unit7_acceptance.py; run_eval's
        # general-purpose bodies validation expects dictionaries only.
        "bodies": [
            {"text": "A complete paragraph to validate.", "creator_id": 1},
            {"text": "A complete paragraph to validate."},
            {"creator_id": "missing-text"},
            {"text": "", "creator_id": "empty-text"},
            {"text": None, "creator_id": "null-text"},
            {"text": "short", "creator_id": "short-text"},
            {"text": "z" * 12001, "creator_id": "oversized-text"},
        ],
    },
]


def validate() -> list[str]:
    """Stop invalid evaluations BEFORE sending requests, with candid errors."""
    problems: list[str] = []
    passages = SCENARIOS[0]["texts"]

    if len(passages) != 10:
        problems.append(
            f"Criterion 1 requires exactly 10 genuinely human-authored passages; "
            f"found {len(passages)} at {ORIGINALS}. No AI-generated substitute."
        )
    for i, text in enumerate(passages, 1):
        if not text.strip() or len(text.strip()) < 20 or len(text) > 12000:
            problems.append(
                f"Authentic passage {i} must contain 20-12,000 characters."
            )

    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} lacks a name")
        if scenario.get("texts") and scenario.get("bodies"):
            problems.append(f"scenario {i} has both texts and bodies")
        for j, body in enumerate(scenario.get("bodies", []), 1):
            if not isinstance(body, dict):
                problems.append(f"scenario {i}, body {j} must be a JSON object")
    return problems


if __name__ == "__main__":
    import sys
    problems = validate()
    if problems:
        for problem in problems:
            print("NOT READY:", problem)
        sys.exit(1)
    print("READY: ten original human passages and bad-input scenarios are configured.")
