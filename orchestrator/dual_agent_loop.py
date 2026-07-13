#!/usr/bin/env python3
"""Dual-agent autonomous development loop orchestrator."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
if _HERE.parent.name == "orchestrator" and _HERE.parents[1].name == "auto":
    REPO_ROOT = _HERE.parents[2]
else:
    REPO_ROOT = _HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from auto.orchestrator.cli_backend import call_agent_cli
from auto.orchestrator.config import load_config, save_config
from auto.orchestrator.notify import notify_owner
from auto.orchestrator.parse import extract_decision, extract_developer_mode, extract_instruction
from auto.orchestrator.prompts import (
    build_developer_prompt,
    build_master_context_prompt,
    build_master_prompt,
    build_master_task_bootstrap_prompt,
    build_prompts_for_config,
    read_guidelines,
)
from auto.orchestrator.sdk_backend import close_sdk_agents, create_sdk_agents, send_developer, send_master
from auto.orchestrator.state import collect_repo_state, write_state_snapshot


def sync_allowlist(config) -> None:
    """Sync write boundary + safety_mode for Cursor hooks."""
    allowlist_path = config.workspace / ".cursor" / "hooks" / "allowlist.json"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sandbox_dir": "auto/sandbox",
        "write_roots": config.write_roots,
        "allowed_paths": config.write_roots,
        "safety_mode": config.safety_mode,
    }
    allowlist_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_log(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{title}\n{body}\n\n")


def _prompt_parts(config):
    return build_prompts_for_config(config)


def _master_ready(text: str) -> bool:
    upper = (text or "").upper()
    if "READY:" in upper and "YES" in upper:
        return True
    return len((text or "").strip()) >= 40 and "NOT READY" not in upper


def _handle_decision(
    config,
    iteration: int,
    decision: str | None,
    instruction: str,
    master_output: str,
) -> tuple[int | None, bool]:
    config.last_iteration = iteration
    config.last_instruction = instruction
    if config.config_path:
        save_config(config)

    print(f"\n=== ITERATION {iteration} ===")
    print(f"Decision: {decision or 'INVALID'}")
    print(instruction)

    if decision is None:
        notify_owner(
            config.run_dir,
            "invalid_decision",
            "Master output missing a parseable DECISION line "
            "(expected DECISION: CONTINUE|FIX|STOP|ESCALATE).\n\n"
            + master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 1, True

    if decision == "STOP":
        notify_owner(
            config.run_dir,
            "complete",
            master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 0, True

    if decision == "ESCALATE":
        notify_owner(
            config.run_dir,
            "needs_input",
            master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 0, True

    return None, False


def _persist_agent_ids(config, agents) -> None:
    if agents is None:
        return
    config.developer_agent_id = agents.developer.agent_id
    config.master_agent_id = agents.master.agent_id
    if config.config_path:
        save_config(config)


def _cli_master_text(config, prompt: str, *, mode: str | None = None) -> str:
    # Default: no --mode plan, so the model returns a full DECISION block.
    return call_agent_cli(
        prompt,
        cwd=config.workspace,
        model=config.model,
        force=False,
        mode=mode,
    )


async def bootstrap_master(config, agents) -> tuple[str | None, int | None]:
    """Master-first bootstrap: File 1 context, then File 2 -> first developer instruction.

    Returns (instruction_for_developer, exit_code_if_stopped).
    """
    protocol, _dev_protocol, escalate, safety = _prompt_parts(config)
    master_instructions = read_guidelines(config.master_instructions)

    print("\n=== BOOTSTRAP 1/2: master context ===")
    context_prompt = build_master_context_prompt(
        master_instructions,
        safety_guidelines=safety,
    )
    if agents is not None:
        context_out = await send_master(agents, context_prompt)
    else:
        context_out = _cli_master_text(config, context_prompt)
    append_log(config.run_dir / "master.log", "BOOTSTRAP 1/2 CONTEXT", context_out)
    _persist_agent_ids(config, agents)

    if not _master_ready(context_out):
        notify_owner(
            config.run_dir,
            "invalid_decision",
            "Master bootstrap context step failed (no READY acknowledgment).\n\n"
            + context_out,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return None, 1

    print("\n=== BOOTSTRAP 2/2: master task -> first developer instruction ===")
    task_prompt = build_master_task_bootstrap_prompt(
        config.task,
        master_protocol=protocol,
        escalate_policy=escalate,
        safety_guidelines=safety,
        max_iterations=config.max_iterations,
    )
    if agents is not None:
        task_out = await send_master(agents, task_prompt)
    else:
        task_out = _cli_master_text(config, task_prompt)
    append_log(config.run_dir / "master.log", "BOOTSTRAP 2/2 TASK", task_out)
    _persist_agent_ids(config, agents)

    decision = extract_decision(task_out)
    boot_mode = extract_developer_mode(task_out)
    if boot_mode:
        config.last_developer_mode = boot_mode
    if decision is None:
        # One corrective retry — plan-mode/status-only replies are common failures
        retry_prompt = (
            "Your previous reply was invalid for the orchestrator.\n"
            "Reply again with ONLY this exact structure (no status preamble):\n\n"
            "DECISION: CONTINUE\n\n"
            "INSTRUCTION_FOR_DEVELOPER:\n"
            "<first concrete developer step from the owner task>\n\n"
            "REASON:\n"
            "<short>\n\n"
            "CHECKS_REQUIRED:\n"
            "<checks or none>\n"
        )
        print("\n=== BOOTSTRAP 2/2 retry: require DECISION block ===")
        if agents is not None:
            task_out = await send_master(agents, retry_prompt)
        else:
            task_out = _cli_master_text(config, retry_prompt)
        append_log(config.run_dir / "master.log", "BOOTSTRAP 2/2 TASK RETRY", task_out)
        _persist_agent_ids(config, agents)
        decision = extract_decision(task_out)
        boot_mode = extract_developer_mode(task_out) or boot_mode
        if boot_mode:
            config.last_developer_mode = boot_mode

    instruction = extract_instruction(task_out)
    config.last_instruction = instruction if decision else None
    if config.config_path:
        save_config(config)

    print(f"Bootstrap decision: {decision or 'INVALID'}")
    print(instruction)

    if decision is None:
        notify_owner(
            config.run_dir,
            "invalid_decision",
            "Master bootstrap task step missing DECISION.\n\n" + task_out,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return None, 1

    if decision == "STOP":
        notify_owner(
            config.run_dir,
            "complete",
            task_out,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return None, 0

    if decision == "ESCALATE":
        notify_owner(
            config.run_dir,
            "needs_input",
            task_out,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return None, 0

    if boot_mode:
        config.last_developer_mode = boot_mode
    elif config.last_developer_mode is None:
        config.last_developer_mode = "agent"
    if config.config_path:
        save_config(config)
    return instruction, None


async def run_developer_turn(
    config,
    agents,
    iteration: int,
    instruction: str,
    *,
    force_dev: bool,
    developer_mode: str | None = None,
) -> str:
    _protocol, developer_protocol, _escalate, safety = _prompt_parts(config)
    inject_owner = None
    if config.owner_reply:
        inject_owner = config.owner_reply
        config.owner_reply = None
        if config.config_path:
            save_config(config)

    # Also allow owner clarification embedded in instruction from resume path
    dev_prompt = build_developer_prompt(
        config.task,
        instruction,
        developer_protocol,
        owner_reply=inject_owner,
        safety_guidelines=safety,
    )
    mode = (developer_mode or config.last_developer_mode or "agent").lower()
    if mode not in {"agent", "plan"}:
        mode = "agent"
    if agents is not None:
        dev_output = await send_developer(agents, dev_prompt, mode=mode)
    else:
        dev_output = call_agent_cli(
            dev_prompt,
            cwd=config.developer_cwd,
            model=config.model,
            force=force_dev,
            mode=("plan" if mode == "plan" else None),
        )
    append_log(
        config.run_dir / "developer.log",
        f"ITERATION {iteration} (mode={mode})",
        dev_output,
    )
    _persist_agent_ids(config, agents)
    return dev_output


async def run_master_review_turn(
    config, agents, iteration: int, developer_output: str
) -> str:
    protocol, _dev, escalate, safety = _prompt_parts(config)
    repo_state = collect_repo_state(config)
    write_state_snapshot(config.run_dir, iteration, repo_state)

    master_prompt = build_master_prompt(
        config.task,
        read_guidelines(config.master_instructions),
        developer_output,
        repo_state,
        iteration,
        config.max_iterations,
        master_protocol=protocol,
        escalate_policy=escalate,
        safety_guidelines=safety,
    )
    if agents is not None:
        master_output = await send_master(agents, master_prompt)
    else:
        master_output = _cli_master_text(config, master_prompt)
    append_log(config.run_dir / "master.log", f"ITERATION {iteration}", master_output)
    _persist_agent_ids(config, agents)
    return master_output


async def run_loop_async(config, *, resume: bool, force_dev: bool) -> int:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    sync_allowlist(config)

    agents = None
    try:
        if config.backend == "sdk":
            agents = await create_sdk_agents(
                repo_root=config.workspace,
                developer_cwd=config.developer_cwd,
                model=config.model,
                developer_agent_id=config.developer_agent_id if resume else None,
                master_agent_id=config.master_agent_id if resume else None,
            )

        if resume and config.last_iteration > 0 and config.last_instruction:
            start = config.last_iteration + 1
            instruction = config.last_instruction
            # owner_reply (if any) is injected once in run_developer_turn
        else:
            instruction, boot_exit = await bootstrap_master(config, agents)
            if boot_exit is not None:
                return boot_exit
            assert instruction is not None
            start = 1

        developer_mode = config.last_developer_mode or "agent"
        for iteration in range(start, config.max_iterations + 1):
            print(f"\n--- Developer turn {iteration} (mode={developer_mode}) ---")
            dev_output = await run_developer_turn(
                config,
                agents,
                iteration,
                instruction,
                force_dev=force_dev,
                developer_mode=developer_mode,
            )
            master_output = await run_master_review_turn(
                config, agents, iteration, dev_output
            )
            decision = extract_decision(master_output)
            instruction = extract_instruction(master_output)
            next_mode = extract_developer_mode(master_output)
            if next_mode:
                developer_mode = next_mode
            config.last_developer_mode = developer_mode
            exit_code, stop = _handle_decision(
                config, iteration, decision, instruction, master_output
            )
            if stop:
                return exit_code if exit_code is not None else 0

        print("\nMaximum iterations reached. Review logs in", config.run_dir)
        notify_owner(
            config.run_dir,
            "max_iterations",
            "Loop reached max_iterations without STOP. "
            "Force-stop anytime with Ctrl+C (or kill the screen session).",
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 1
    finally:
        if agents is not None:
            dev_id, master_id = await close_sdk_agents(agents)
            config.developer_agent_id = dev_id
            config.master_agent_id = master_id
            if config.config_path:
                save_config(config)


def run_loop(config, *, resume: bool, force_dev: bool) -> int:
    return asyncio.run(run_loop_async(config, resume=resume, force_dev=force_dev))


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual-agent autonomous development loop")
    parser.add_argument("--config", required=True, help="Path to task config.yaml")
    parser.add_argument("--resume", action="store_true", help="Resume from saved iteration state")
    parser.add_argument("--force", action="store_true", help="Allow developer file writes (CLI backend)")
    parser.add_argument("--backend", choices=("sdk", "cli"), default=None, help="Override config backend")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    if args.backend:
        config.backend = args.backend

    if config.backend == "sdk" and not os.environ.get("CURSOR_API_KEY"):
        print("CURSOR_API_KEY is required for SDK backend", file=sys.stderr)
        return 1

    os.environ.setdefault(
        "PATH",
        os.environ.get("PATH", "") + os.pathsep + str(Path.home() / ".local" / "bin"),
    )

    return run_loop(config, resume=args.resume, force_dev=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
