"""Parse structured agent output."""

from __future__ import annotations

import re

_DECISION_RE = re.compile(
    r"(?im)^\s*DECISION:\s*(CONTINUE|FIX|STOP|ESCALATE)\s*$"
)


def extract_decision(text: str) -> str | None:
    """Return an explicit DECISION value, or None if missing/malformed."""
    matches = _DECISION_RE.findall(text or "")
    if not matches:
        return None
    return matches[-1].upper()


def extract_instruction(text: str, marker: str = "INSTRUCTION_FOR_DEVELOPER:") -> str:
    index = text.find(marker)
    if index == -1:
        return (text or "").strip()
    instruction = text[index + len(marker) :].strip()
    for next_marker in ("REASON:", "CHECKS_REQUIRED:", "DECISION:"):
        marker_index = instruction.find(next_marker)
        if marker_index > 0:
            instruction = instruction[:marker_index].strip()
    return instruction.strip() or (text or "").strip()
