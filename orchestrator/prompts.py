"""Prompt builders for developer and master agents."""

from __future__ import annotations

from pathlib import Path


def read_guidelines(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def build_developer_prompt(
    task: str,
    instruction: str,
    developer_guidelines: str,
    *,
    owner_reply: str | None = None,
) -> str:
    owner_block = ""
    if owner_reply:
        owner_block = f"\nOwner clarification (treat as authoritative):\n{owner_reply}\n"
    return f"""
You are the Developer Agent.

Use these project guidelines:
{developer_guidelines}

Original task:
{task}
{owner_block}
Master instruction:
{instruction}

Follow .cursor/agents/developer.md.

Perform one coherent implementation step, verify it, and stop with STATUS, CHANGES, VERIFICATION, and NEXT.
""".strip()


def build_master_prompt(
    task: str,
    master_guidelines: str,
    developer_output: str,
    repo_state: str,
    current_iteration: int,
    max_iterations: int,
) -> str:
    return f"""
You are the Master Agent.

Use these project guidelines:
{master_guidelines}

Original task:
{task}

Current iteration:
{current_iteration} of {max_iterations}

Developer output:
{developer_output}

Repository state:
{repo_state}

Follow .cursor/agents/master.md.

Return DECISION, INSTRUCTION_FOR_DEVELOPER, REASON, and CHECKS_REQUIRED.

Important:
- Return STOP only if the task is complete and verification is acceptable.
- Return ESCALATE only if a real human decision is required.
- Otherwise return CONTINUE or FIX with the exact next instruction for the developer.
""".strip()
