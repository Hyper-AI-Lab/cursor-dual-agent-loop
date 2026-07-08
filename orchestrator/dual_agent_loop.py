#!/usr/bin/env python3
"""Dual-agent autonomous development loop orchestrator."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from auto.orchestrator.cli_backend import call_agent_cli
from auto.orchestrator.config import load_config, save_config
from auto.orchestrator.notify import notify_owner
from auto.orchestrator.parse import extract_decision, extract_instruction
from auto.orchestrator.prompts import build_developer_prompt, build_master_prompt, read_guidelines
from auto.orchestrator.sdk_backend import close_sdk_agents, create_sdk_agents, send_developer, send_master
from auto.orchestrator.state import collect_repo_state, write_state_snapshot


def sync_allowlist(config) -> None:
    allowlist_path = config.repo_root / ".cursor" / "hooks" / "allowlist.json"
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sandbox_dir": str(config.sandbox_dir.relative_to(config.repo_root)),
        "allowed_paths": config.allowed_paths,
    }
    allowlist_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_log(path: Path, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{title}\n{body}\n\n")


def run_cli_iteration(config, iteration: int, instruction: str, *, force_dev: bool) -> str:
    dev_prompt = build_developer_prompt(
        config.task,
        instruction,
        read_guidelines(config.developer_guidelines),
        owner_reply=config.owner_reply if iteration == config.last_iteration + 1 else None,
    )
    dev_output = call_agent_cli(
        dev_prompt,
        cwd=config.developer_cwd,
        model=config.model,
        force=force_dev,
    )
    append_log(config.run_dir / "developer.log", f"ITERATION {iteration}", dev_output)

    repo_state = collect_repo_state(config)
    write_state_snapshot(config.run_dir, iteration, repo_state)

    master_prompt = build_master_prompt(
        config.task,
        read_guidelines(config.master_guidelines),
        dev_output,
        repo_state,
        iteration,
        config.max_iterations,
    )
    master_output = call_agent_cli(
        master_prompt,
        cwd=config.repo_root,
        model=config.model,
        force=False,
        mode="plan",
    )
    append_log(config.run_dir / "master.log", f"ITERATION {iteration}", master_output)
    return master_output


async def run_sdk_iteration(agents, config, iteration: int, instruction: str) -> str:
    dev_prompt = build_developer_prompt(
        config.task,
        instruction,
        read_guidelines(config.developer_guidelines),
        owner_reply=config.owner_reply if iteration == config.last_iteration + 1 else None,
    )
    dev_output = await send_developer(agents, dev_prompt)
    append_log(config.run_dir / "developer.log", f"ITERATION {iteration}", dev_output)

    repo_state = collect_repo_state(config)
    write_state_snapshot(config.run_dir, iteration, repo_state)

    master_prompt = build_master_prompt(
        config.task,
        read_guidelines(config.master_guidelines),
        dev_output,
        repo_state,
        iteration,
        config.max_iterations,
    )
    master_output = await send_master(agents, master_prompt)
    append_log(config.run_dir / "master.log", f"ITERATION {iteration}", master_output)
    return master_output


def _handle_decision(
    config,
    iteration: int,
    decision: str,
    instruction: str,
    master_output: str,
    fix_streak: int,
) -> tuple[int | None, int, bool]:
    if decision == "FIX":
        fix_streak += 1
    else:
        fix_streak = 0

    config.last_iteration = iteration
    config.last_instruction = instruction
    if config.config_path:
        save_config(config)

    print(f"\n=== ITERATION {iteration} ===")
    print(f"Decision: {decision}")
    print(instruction)

    if decision == "STOP":
        notify_owner(
            config.run_dir,
            "complete",
            master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 0, fix_streak, True

    if decision == "ESCALATE":
        notify_owner(
            config.run_dir,
            "needs_input",
            master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 0, fix_streak, True

    if fix_streak >= config.max_consecutive_fixes:
        notify_owner(
            config.run_dir,
            "stuck",
            master_output,
            write_needs_owner=config.notify.write_needs_owner,
            webhook_url=config.notify.webhook_url,
            task_id=config.task_id,
        )
        return 1, fix_streak, True

    return None, fix_streak, False


async def run_loop_async(config, *, resume: bool, force_dev: bool) -> int:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    sync_allowlist(config)

    start = config.last_iteration + 1 if resume else 1
    instruction = config.last_instruction or config.initial_instruction
    if resume and config.owner_reply:
        instruction = f"{instruction}\n\nOwner clarification:\n{config.owner_reply}"
        config.owner_reply = None

    fix_streak = 0
    agents = None

    try:
        if config.backend == "sdk":
            agents = await create_sdk_agents(
                repo_root=config.repo_root,
                developer_cwd=config.developer_cwd,
                model=config.model,
                developer_agent_id=config.developer_agent_id if resume else None,
                master_agent_id=config.master_agent_id if resume else None,
            )

        for iteration in range(start, config.max_iterations + 1):
            if config.backend == "sdk":
                assert agents is not None
                master_output = await run_sdk_iteration(agents, config, iteration, instruction)
            else:
                master_output = run_cli_iteration(config, iteration, instruction, force_dev=force_dev)

            decision = extract_decision(master_output)
            instruction = extract_instruction(master_output)

            exit_code, fix_streak, stop = _handle_decision(
                config, iteration, decision, instruction, master_output, fix_streak
            )
            if agents is not None:
                config.developer_agent_id = agents.developer.agent_id
                config.master_agent_id = agents.master.agent_id
                if config.config_path:
                    save_config(config)
            if stop:
                return exit_code if exit_code is not None else 0

        print("\nMaximum iterations reached. Review logs in", config.run_dir)
        notify_owner(
            config.run_dir,
            "max_iterations",
            "Loop reached max_iterations without STOP.",
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


async def _run_cli_loop(config, *, resume: bool, force_dev: bool) -> int:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    sync_allowlist(config)

    start = config.last_iteration + 1 if resume else 1
    instruction = config.last_instruction or config.initial_instruction
    if resume and config.owner_reply:
        instruction = f"{instruction}\n\nOwner clarification:\n{config.owner_reply}"
        config.owner_reply = None

    fix_streak = 0
    for iteration in range(start, config.max_iterations + 1):
        master_output = run_cli_iteration(config, iteration, instruction, force_dev=force_dev)
        decision = extract_decision(master_output)
        instruction = extract_instruction(master_output)
        exit_code, fix_streak, stop = _handle_decision(
            config, iteration, decision, instruction, master_output, fix_streak
        )
        if stop:
            return exit_code if exit_code is not None else 0

    print("\nMaximum iterations reached. Review logs in", config.run_dir)
    return 1


def run_loop(config, *, resume: bool, force_dev: bool) -> int:
    if config.backend == "sdk":
        return asyncio.run(run_loop_async(config, resume=resume, force_dev=force_dev))
    return asyncio.run(_run_cli_loop(config, resume=resume, force_dev=force_dev))


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
