"""Tests for dual-agent orchestrator helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from auto.orchestrator.boundary import extract_tool_path, path_is_allowed
from auto.orchestrator.config import load_config, save_config
from auto.orchestrator.parse import extract_decision, extract_developer_mode, extract_instruction


REPO = Path(__file__).resolve().parents[1]


def test_extract_decision_prefers_explicit_marker():
    text = "DECISION: STOP\nINSTRUCTION_FOR_DEVELOPER:\nDone."
    assert extract_decision(text) == "STOP"


def test_extract_decision_fix_before_continue():
    text = "DECISION: FIX\nSome CONTINUE mention in reason."
    assert extract_decision(text) == "FIX"


def test_extract_decision_missing_returns_none():
    text = "I think we should continue somehow."
    assert extract_decision(text) is None


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


def test_path_is_allowed_workspace_root():
    repo = REPO
    assert path_is_allowed(
        repo,
        repo / "app" / "routers" / "assets.py",
        write_roots=["."],
    )


def test_path_is_allowed_narrow_roots():
    repo = REPO
    target = repo / "app" / "routers" / "foo.py"
    assert not path_is_allowed(repo, target, write_roots=["auto/sandbox"])
    assert path_is_allowed(
        repo,
        repo / "auto" / "sandbox" / "hello.py",
        write_roots=["auto/sandbox"],
    )


def test_path_is_allowed_auto_runs_implicit():
    repo = REPO
    target = repo / "auto" / "runs" / "my-task" / "config.yaml"
    assert path_is_allowed(repo, target, write_roots=["auto/sandbox"])


def test_extract_tool_path_write():
    assert extract_tool_path("Write", {"path": "auto/sandbox/x.py"}) == "auto/sandbox/x.py"


def test_load_minimal_config_and_save(tmp_path: Path):
    master = tmp_path / "master.md"
    task = tmp_path / "task.md"
    master.write_text("master context", encoding="utf-8")
    task.write_text("do the thing", encoding="utf-8")
    # Place config under a fake runs dir but point workspace via absolute path in yaml
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump(
            {
                "task_id": "t1",
                "workspace": str(REPO),
                "model": "auto",
                "max_iterations": 5,
                "backend": "cli",
                "master_instructions": str(master),
                "task": str(task),
                "write_roots": ["."],
                "safety_mode": "off",
            }
        ),
        encoding="utf-8",
    )
    config = load_config(cfg_file)
    assert config.task_id == "t1"
    assert config.backend == "cli"
    assert config.task == "do the thing"
    assert config.safety_mode == "off"
    assert "max_consecutive_fixes" not in config.__dataclass_fields__
    config.last_iteration = 2
    config.developer_agent_id = "agent-test"
    save_config(config)
    assert (config.run_dir / "run_state.yaml").exists()
    # Owner config.yaml must not be clobbered
    assert "task_id: t1" in cfg_file.read_text(encoding="utf-8")
    reloaded = load_config(cfg_file)
    assert reloaded.last_iteration == 2
    assert reloaded.developer_agent_id == "agent-test"
    assert reloaded.task == "do the thing"


def test_load_explore_1_config():
    import pytest

    cfg = REPO / "auto" / "runs" / "explore_1" / "config.yaml"
    if not cfg.exists():
        pytest.skip("explore_1 run config only present in DarkHerd checkout")
    config = load_config(cfg)
    assert config.task_id == "explore_1"
    assert config.workspace == REPO
    assert config.write_roots == ["."]
    assert config.safety_mode == "off"
    assert "Phase 0" in config.task or "Phase 1" in config.task
    assert config.master_instructions.exists()


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


def test_notify_invalid_decision(tmp_path: Path):
    from auto.orchestrator.notify import notify_owner

    path = notify_owner(
        tmp_path,
        "invalid_decision",
        "no decision line",
        write_needs_owner=True,
        task_id="demo",
    )
    assert path is not None
    assert path.name == "NEEDS_OWNER.md"


def test_master_bootstrap_prompts():
    from auto.orchestrator.prompts import (
        build_master_context_prompt,
        build_master_task_bootstrap_prompt,
    )

    ctx = build_master_context_prompt("Know the repo.", safety_guidelines="Be safe.")
    assert "bootstrap step 1" in ctx.lower() or "Bootstrap step 1" in ctx
    assert "READY: yes" in ctx
    assert "Know the repo." in ctx
    assert "DECISION:" not in ctx.split("Do not output")[0] or "Do not output DECISION" in ctx

    task = build_master_task_bootstrap_prompt(
        "Explore Phase 0.",
        master_protocol="proto",
        escalate_policy="esc",
        safety_guidelines="safe",
    )
    assert "bootstrap step 2" in task.lower() or "Bootstrap step 2" in task
    assert "Explore Phase 0." in task
    assert "DECISION: CONTINUE" in task
    assert "INSTRUCTION_FOR_DEVELOPER:" in task


def test_master_ready_helper():
    from auto.orchestrator.dual_agent_loop import _master_ready

    assert _master_ready("READY: yes\nSUMMARY:\n- a\n- b")
    assert not _master_ready("nope")


def test_extract_developer_mode():
    text = """DECISION: CONTINUE
DEVELOPER_MODE: plan
INSTRUCTION_FOR_DEVELOPER:
Do research only.
"""
    assert extract_developer_mode(text) == "plan"
    assert extract_instruction(text) == "Do research only."
    assert extract_developer_mode("DECISION: CONTINUE\nNo mode here") is None


def test_master_prompts_omit_iteration_budget():
    from auto.orchestrator.prompts import (
        build_master_prompt,
        build_master_task_bootstrap_prompt,
    )

    boot = build_master_task_bootstrap_prompt("Do the work.")
    assert "Loop budget" not in boot
    assert "up to {" not in boot
    assert "Do **not** compress" in boot

    review = build_master_prompt(
        "Do the work.",
        "master ctx",
        "developer said done",
        "git clean",
    )
    assert "Current iteration" not in review
    assert "Loop budget" not in review
    assert "not be told an iteration cap" in review
    assert "fit a budget" in review
    # Protocol may name the config key only to tell the master to ignore it
    assert "kill-switch" in review or "orchestrator" in review.lower()
