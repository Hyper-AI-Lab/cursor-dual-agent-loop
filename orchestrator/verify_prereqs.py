#!/usr/bin/env python3
"""Smoke test for Cursor CLI/SDK prerequisites."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    agent_bin = shutil.which("agent") or shutil.which("cursor-agent")
    if not agent_bin:
        print("FAIL: Cursor CLI (agent) not found on PATH")
        return 1
    print(f"OK: CLI at {agent_bin}")

    try:
        import cursor_sdk  # noqa: F401
    except ImportError:
        print("FAIL: cursor-sdk not installed")
        return 1
    print("OK: cursor-sdk installed")

    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        print("SKIP: CURSOR_API_KEY not set — set it to run live Agent.prompt smoke test")
        return 0

    from auto.orchestrator.sdk_backend import sync_prompt

    try:
        reply = sync_prompt("Reply with exactly: OK", cwd=REPO_ROOT, model="composer-2.5")
    except Exception as exc:
        print(f"FAIL: Agent.prompt smoke test failed: {exc}")
        return 1

    print(f"OK: Agent.prompt replied: {reply[:80]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
