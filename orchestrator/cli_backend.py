"""CLI backend for dual-agent loop."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def call_agent_cli(
    prompt: str,
    *,
    cwd: Path,
    model: str,
    force: bool = False,
    mode: str | None = None,
    cursor_bin: str | None = None,
    timeout: int | None = None,
) -> str:
    bin_path = cursor_bin or os.environ.get("CURSOR_BIN", "agent")
    command = [bin_path, "-p"]
    command.extend(["--model", model])
    if mode:
        command.extend(["--mode", mode])
    if force:
        command.append("--force")
    command.append(prompt)

    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    output = (result.stdout or "").strip()
    if result.returncode != 0 and not output:
        raise RuntimeError(f"agent CLI failed with exit {result.returncode}")
    return output
