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
Owner task (for context; follow the master instruction for this turn):
{task}
{owner_block}
Master instruction:
{instruction}

Perform one coherent step, verify it when practical, and stop with STATUS, CHANGES, VERIFICATION, and NEXT.
""".strip()


def build_master_context_prompt(
    master_instructions: str,
    *,
    safety_guidelines: str = "",
) -> str:
    """Bootstrap step 1: load File 1 (master context) before any task/developer work."""
    return f"""
You are the Master Agent. This is bootstrap step 1 of 2 (context only).

Read and internalize the owner-provided master instructions below. Do not plan the full
project yet and do not invent developer work. Absorb operating context only.

Safety guidelines:
{safety_guidelines}

Owner-provided master instructions:
{master_instructions}

When finished, reply with exactly:

READY: yes
SUMMARY:
<3-8 bullet points of what you will keep in mind while supervising>

Do not output DECISION yet. Do not instruct the developer yet.
""".strip()


def build_master_task_bootstrap_prompt(
    task: str,
    *,
    master_protocol: str = "",
    escalate_policy: str = "",
    safety_guidelines: str = "",
) -> str:
    """Bootstrap step 2: File 2 (task) → first developer instruction."""
    protocol = master_protocol or read_guidelines(BUILTIN_DIR / "master_protocol.md")
    return f"""
You are the Master Agent. This is bootstrap step 2 of 2 (task → first developer prompt).

You already received master context in the previous message. Now read the owner task below,
derive the plan, acceptance/finish criteria, and the first concrete developer instruction.

Built-in protocol:
{protocol}

Escalate policy:
{escalate_policy}

Safety guidelines:
{safety_guidelines}

Owner task (goals / targets / how to drive the developer):
{task}

Plan for quality and correctness. Do **not** compress or rush work to fit an iteration
budget — the orchestrator enforces any hard stop separately; you must not treat a turn
limit as a completion criterion.

Your entire reply MUST be exactly these sections (no other preamble or status text):

DECISION: CONTINUE

DEVELOPER_MODE: agent

INSTRUCTION_FOR_DEVELOPER:
<exact first prompt for the developer>

REASON:
<short explanation>

CHECKS_REQUIRED:
<checks for this step, or none>

Important:
- Prefer DECISION: CONTINUE with the first developer step, unless escalate policy applies.
- Do not return STOP unless the task is already complete with no work needed.
- Do not reply with only a planning status sentence — the orchestrator parses DECISION strictly.
""".strip()


def build_master_prompt(
    task: str,
    master_guidelines: str,
    developer_output: str,
    repo_state: str,
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

Developer output:
{developer_output}

Repository / workspace state (inspect further yourself when needed):
{repo_state}

Return DECISION, INSTRUCTION_FOR_DEVELOPER, REASON, and CHECKS_REQUIRED.
Optionally include DEVELOPER_MODE: agent|plan.

Important:
- Optimize for productivity, efficiency, and accuracy — not for finishing in fewer turns.
- Do **not** STOP early to "fit a budget". STOP only when the owner task is truly complete
  by your derived quality criteria. If more honest work remains, CONTINUE or FIX.
- You will not be told an iteration cap; ignore any urge to compress scope for turn limits.
- Inspect artifacts when claims matter; do not trust developer prose alone.
- If the developer asked a multiple-choice / Needs decision question, answer it in
  INSTRUCTION_FOR_DEVELOPER (or ESCALATE to the owner when required).
- Optionally set DEVELOPER_MODE: agent|plan for the next developer turn (default agent).
- Return ESCALATE only when the escalate policy applies.
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
