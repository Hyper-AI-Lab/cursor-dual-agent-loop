"""Collect repository state for master review."""

from __future__ import annotations

import subprocess
from pathlib import Path

from auto.orchestrator.config import LoopConfig


def _run_shell(command: str, cwd: Path, timeout: int = 600) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        exit_note = f"\n[exit code: {result.returncode}]"
        output = (result.stdout or "").strip()
        return (output + exit_note).strip()
    except subprocess.TimeoutExpired:
        return f"[command timed out after {timeout}s]"


def collect_repo_state(config: LoopConfig) -> str:
    repo = config.repo_root
    scope = " ".join(f"'{p}'" for p in config.state_scope_paths)
    parts: list[str] = []

    parts.append("GIT STATUS (scoped):")
    parts.append(_run_shell(f"git status --short -- {scope}", cwd=repo, timeout=30))

    parts.append("\nGIT DIFF STAT (scoped):")
    parts.append(_run_shell(f"git diff --stat -- {scope}", cwd=repo, timeout=30))

    parts.append("\nGIT DIFF (scoped, truncated):")
    diff = _run_shell(f"git diff -- {scope}", cwd=repo, timeout=60)
    parts.append(diff[-30000:])

    if config.lint_command:
        parts.append("\nLINT RESULT:")
        parts.append(_run_shell(config.lint_command, cwd=repo, timeout=300))

    if config.test_command:
        parts.append("\nTEST RESULT:")
        parts.append(_run_shell(config.test_command, cwd=repo, timeout=600))

    return "\n".join(parts)


def write_state_snapshot(run_dir: Path, iteration: int, state: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"state_{iteration:03d}.txt").write_text(state, encoding="utf-8")
