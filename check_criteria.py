#!/usr/bin/env python3
"""Pre-submission structural check for five Unit 7 acceptance criteria.

This is a structural checker, not an AI criterion generator or a grader.
It checks that each numbered item has a meaningful statement and a reason;
the student must personally review, defend, and validate acceptance targets.

Usage:
    python check_criteria.py
    python check_criteria.py path/to/criteria.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEADING = re.compile(r"(?m)^##[ \t]+([1-5])\.[ \t]*([^\n]*)$")
REASON = re.compile(r"\*\*Why this target:\*\*", re.IGNORECASE)
NUMERIC = re.compile(r"(?<!\w)\d+(?:\.\d+)?(?:\s*%)?(?!\w)")


def check(path: Path) -> int:
    if not path.is_file():
        print(f"ERROR: Could not find {path}")
        return 1

    # Ignore the starter's HTML comments, including Unit 8 examples.
    source = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    headings = list(HEADING.finditer(source))
    problems: list[str] = []

    numbers = [int(m.group(1)) for m in headings]
    if numbers != [1, 2, 3, 4, 5]:
        problems.append(f"Expected exactly five ordered headings ## 1. to ## 5.; found {numbers}.")

    for index, match in enumerate(headings):
        number = match.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = source[match.end():end].strip()
        parts = REASON.split(section, maxsplit=1)

        # Allow a descriptive heading such as '## 1. Human false-positive limit'.
        statement = (match.group(2) + " " + parts[0]).strip()
        words = re.findall(r"\b[\w'-]+\b", statement, flags=re.UNICODE)
        if len(words) < 8:
            problems.append(f"Criterion {number}: write a concrete, checkable statement (currently too short/empty).")

        if len(parts) < 2:
            problems.append(f"Criterion {number}: add '**Why this target:**' and your justification.")
        else:
            explanation = parts[1].strip()
            if len(re.findall(r"\b[\w'-]+\b", explanation, flags=re.UNICODE)) < 6:
                problems.append(f"Criterion {number}: explain why you chose this target.")

        # Advisory only: some excellent criteria describe an observable event
        # rather than a numeral. Only the writer can judge the target.
        if len(words) >= 8 and not NUMERIC.search(statement):
            print(f"REVIEW criterion {number}: no number found; make sure its outcome is plainly observable.")

    if problems:
        print("NOT READY — criteria.md needs complete proposed targets:\n")
        for item in problems:
            print(" - " + item)
        print("\nReview and personally choose five measurable targets before Unit 8 evaluation.")
        return 1

    print("STRUCTURE COMPLETE: five numbered statements and five justifications found.")
    print("Manual review is required: Are targets observable and defensible, and have you personally chosen them?")
    print("This does not test model accuracy or replace the course's acceptance-criteria review.")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("criteria.md")
    raise SystemExit(check(target))
