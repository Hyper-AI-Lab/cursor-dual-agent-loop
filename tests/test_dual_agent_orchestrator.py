"""Tests for dual-agent orchestrator helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from auto.orchestrator.boundary import extract_tool_path, path_is_allowed
from auto.orchestrator.config import load_config, save_config
from auto.orchestrator.parse import extract_decision, extract_instruction


REPO = Path(__file__).resolve().parents[1]


def test_extract_decision_prefers_explicit_marker():
    text = "DECISION: STOP\nINSTRUCTION_FOR_DEVELOPER:\nDone."
    assert extract_decision(text) == "STOP"


def test_extract_decision_fix_before_continue():
    text = "DECISION: FIX\nSome CONTINUE mention in reason."
    assert extract_decision(text) == "FIX"


def test_extract_instruction_strips_trailing_sections():
    text = """
DECISION: CONTINUE
INSTRUCTION_FOR_DEVELOPER:
Implement the next step.
REASON:
Because tests passed.
CHECKS_REQUIRED:
pytest -q
"""
    assert extract_instruction(text) == "Implement the next step."


def test_path_is_allowed_sandbox():
    repo = REPO
    sandbox = repo / "auto" / "sandbox"
    assert path_is_allowed(
        repo,
        sandbox / "hello.py",
        sandbox_dir=sandbox,
        allowed_paths=[],
    )


def test_path_is_allowed_extra_path():
    repo = REPO
    sandbox = repo / "auto" / "sandbox"
    target = repo / "app" / "routers" / "foo.py"
    assert not path_is_allowed(repo, target, sandbox_dir=sandbox, allowed_paths=[])
    assert path_is_allowed(
        repo,
        target,
        sandbox_dir=sandbox,
        allowed_paths=["app/routers/foo.py"],
    )


def test_extract_tool_path_write():
    assert extract_tool_path("Write", {"path": "auto/sandbox/x.py"}) == "auto/sandbox/x.py"


def test_load_and_save_config(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "task_id": "t1",
                "task": "Do something",
                "repo_root": str(REPO),
                "sandbox_dir": "auto/sandbox",
                "backend": "cli",
            }
        ),
        encoding="utf-8",
    )
    config = load_config(cfg_file)
    assert config.task_id == "t1"
    assert config.backend == "cli"
    config.last_iteration = 2
    save_config(config)
    reloaded = load_config(cfg_file)
    assert reloaded.last_iteration == 2


def test_sandbox_boundary_hook_allows_orchestrator(tmp_path: Path):
    repo = REPO
    sandbox = repo / "auto" / "sandbox"
    orchestrator_file = repo / "auto" / "orchestrator" / "dual_agent_loop.py"
    assert path_is_allowed(
        repo,
        orchestrator_file,
        sandbox_dir=sandbox,
        allowed_paths=["auto/orchestrator"],
    )


def test_notify_writes_needs_owner(tmp_path: Path):
    from auto.orchestrator.notify import notify_owner

    path = notify_owner(
        tmp_path,
        "needs_input",
        "Please clarify API shape.",
        write_needs_owner=True,
        task_id="demo",
    )
    assert path is not None
    assert path.name == "NEEDS_OWNER.md"
    assert path.exists()
    assert "owner_reply" in path.read_text(encoding="utf-8")


def test_notify_writes_complete_on_stop(tmp_path: Path):
    from auto.orchestrator.notify import notify_owner

    path = notify_owner(
        tmp_path,
        "complete",
        "DECISION: STOP\nTask done.",
        write_needs_owner=True,
        task_id="demo",
    )
    assert path is not None
    assert path.name == "COMPLETE.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "Task complete" in text
    assert "owner_reply" not in text
