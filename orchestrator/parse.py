"""Parse structured agent output."""

from __future__ import annotations


def extract_decision(text: str) -> str:
    normalized = text.upper()
    for decision in ("STOP", "ESCALATE", "FIX", "CONTINUE"):
        if f"DECISION:\n{decision}" in normalized:
            return decision
        if f"DECISION: {decision}" in normalized:
            return decision
    for decision in ("STOP", "ESCALATE", "FIX", "CONTINUE"):
        if decision in normalized.split():
            return decision
    return "CONTINUE"


def extract_instruction(text: str, marker: str = "INSTRUCTION_FOR_DEVELOPER:") -> str:
    index = text.find(marker)
    if index == -1:
        return text.strip()
    instruction = text[index + len(marker) :].strip()
    for next_marker in ("REASON:", "CHECKS_REQUIRED:", "DECISION:"):
        marker_index = instruction.find(next_marker)
        if marker_index > 0:
            instruction = instruction[:marker_index].strip()
    return instruction.strip() or text.strip()
