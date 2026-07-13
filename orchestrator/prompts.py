"""Prompt builders for developer and master agents."""

from __future__ import annotations

from pathlib import Path

from auto.orchestrator.config import BUILTIN_DIR, LoopConfig


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
    safety_guidelines: str = "",
) -> str:
    owner_block = ""
    if owner_reply:
        owner_block = f"\nOwner clarification (treat as authoritative):\n{owner_reply}\n"
    safety_block = f"\nSafety guidelines:\n{safety_guidelines}\n" if safety_guidelines else ""
    return f"""
You are the Developer Agent.

Built-in protocol:
{developer_guidelines}
{safety_block}
Owner task:
{task}
{owner_block}
Master instruction:
{instruction}

Perform one coherent step, verify it when practical, and stop with STATUS, CHANGES, VERIFICATION, and NEXT.
""".strip()


def build_master_prompt(
    task: str,
    master_guidelines: str,
    developer_output: str,
    repo_state: str,
    current_iteration: int,
    max_iterations: int,
    *,
    master_protocol: str = "",
    escalate_policy: str = "",
    safety_guidelines: str = "",
) -> str:
    protocol = master_protocol or read_guidelines(BUILTIN_DIR / "master_protocol.md")
    return f"""
You are the Master Agent.

Built-in protocol:
{protocol}

Escalate policy:
{escalate_policy}

Safety guidelines:
{safety_guidelines}

Owner-provided master instructions (context / operating knowledge):
{master_guidelines}

Owner task (derive the plan, checks, and completion criteria from this):
{task}

Current iteration:
{current_iteration} of {max_iterations}

Developer output:
{developer_output}

Repository / workspace state (inspect further yourself when needed):
{repo_state}

Return DECISION, INSTRUCTION_FOR_DEVELOPER, REASON, and CHECKS_REQUIRED.

Important:
- Inspect artifacts when claims matter; do not trust developer prose alone.
- Return STOP only if the task is complete by your derived criteria.
- Return ESCALATE only when the escalate policy applies.
- Otherwise return CONTINUE or FIX with the exact next developer instruction.
- Your reply MUST include a line: DECISION: CONTINUE|FIX|STOP|ESCALATE
""".strip()


def build_prompts_for_config(config: LoopConfig) -> tuple[str, str, str, str]:
    """Return (master_protocol, developer_protocol, escalate, safety)."""
    return (
        read_guidelines(BUILTIN_DIR / "master_protocol.md"),
        read_guidelines(BUILTIN_DIR / "developer_protocol.md"),
        read_guidelines(config.escalate_policy),
        read_guidelines(config.safety_guidelines),
    )
