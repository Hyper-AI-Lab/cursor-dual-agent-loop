"""Load and validate dual-agent loop configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class NotifyConfig:
    write_needs_owner: bool = True
    webhook_url: str | None = None


@dataclass
class LoopConfig:
    task_id: str
    task: str
    repo_root: Path
    sandbox_dir: Path
    workspace_mode: str
    allowed_paths: list[str]
    master_guidelines: Path
    developer_guidelines: Path
    model: str
    backend: str
    test_command: str | None
    lint_command: str | None
    max_iterations: int
    max_consecutive_fixes: int
    initial_instruction: str
    owner_reply: str | None
    notify: NotifyConfig
    run_dir: Path
    developer_agent_id: str | None = None
    master_agent_id: str | None = None
    last_iteration: int = 0
    last_instruction: str | None = None
    brief_file: Path | None = None
    config_path: Path | None = None

    @property
    def developer_cwd(self) -> Path:
        if self.workspace_mode == "greenfield":
            return self.sandbox_dir
        return self.repo_root

    @property
    def state_scope_paths(self) -> list[str]:
        paths = [str(self.sandbox_dir.relative_to(self.repo_root))]
        paths.extend(self.allowed_paths)
        return paths


def _resolve(repo_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def load_config(config_path: Path) -> LoopConfig:
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    repo_root = Path(raw.get("repo_root", ".")).resolve()
    if not repo_root.is_absolute():
        repo_root = (config_path.parent / repo_root).resolve()

    sandbox_rel = raw.get("sandbox_dir", "auto/sandbox")
    sandbox_dir = (repo_root / sandbox_rel).resolve()

    task = raw.get("task", "").strip()
    brief_file = _resolve(repo_root, raw.get("brief_file"))
    if brief_file and brief_file.exists():
        task = brief_file.read_text(encoding="utf-8").strip()

    if not task:
        raise ValueError("config must define task or brief_file")

    task_id = raw.get("task_id") or config_path.parent.name
    run_dir_raw = raw.get("run_dir")
    if run_dir_raw:
        run_dir = _resolve(repo_root, run_dir_raw) or (repo_root / "auto/runs" / task_id)
    else:
        run_dir = (repo_root / "auto/runs" / task_id).resolve()

    notify_raw = raw.get("notify") or {}
    notify = NotifyConfig(
        write_needs_owner=bool(notify_raw.get("write_needs_owner", True)),
        webhook_url=notify_raw.get("webhook_url"),
    )

    return LoopConfig(
        task_id=task_id,
        task=task,
        repo_root=repo_root,
        sandbox_dir=sandbox_dir,
        workspace_mode=raw.get("workspace_mode", "constrained"),
        allowed_paths=list(raw.get("allowed_paths") or []),
        master_guidelines=_resolve(repo_root, raw.get("master_guidelines", "auto/guidelines/master.md")) or repo_root / "auto/guidelines/master.md",
        developer_guidelines=_resolve(repo_root, raw.get("developer_guidelines", "auto/guidelines/developer.md")) or repo_root / "auto/guidelines/developer.md",
        model=raw.get("model", "composer-2.5"),
        backend=raw.get("backend", "sdk"),
        test_command=raw.get("test_command"),
        lint_command=raw.get("lint_command"),
        max_iterations=int(raw.get("max_iterations", 8)),
        max_consecutive_fixes=int(raw.get("max_consecutive_fixes", 3)),
        initial_instruction=(raw.get("initial_instruction") or "").strip() or "Start the task with the first implementation step.",
        owner_reply=(raw.get("owner_reply") or "").strip() or None,
        notify=notify,
        run_dir=run_dir,
        developer_agent_id=raw.get("developer_agent_id"),
        master_agent_id=raw.get("master_agent_id"),
        last_iteration=int(raw.get("last_iteration", 0)),
        last_instruction=raw.get("last_instruction"),
        brief_file=brief_file,
        config_path=config_path.resolve(),
    )


def save_config(config: LoopConfig) -> None:
    if not config.config_path:
        raise ValueError("config_path is required to save")
    data: dict[str, Any] = {
        "task_id": config.task_id,
        "task": config.task,
        "repo_root": ".",
        "sandbox_dir": str(config.sandbox_dir.relative_to(config.repo_root)),
        "workspace_mode": config.workspace_mode,
        "allowed_paths": config.allowed_paths,
        "master_guidelines": str(config.master_guidelines.relative_to(config.repo_root)),
        "developer_guidelines": str(config.developer_guidelines.relative_to(config.repo_root)),
        "model": config.model,
        "backend": config.backend,
        "test_command": config.test_command,
        "lint_command": config.lint_command,
        "max_iterations": config.max_iterations,
        "max_consecutive_fixes": config.max_consecutive_fixes,
        "initial_instruction": config.initial_instruction,
        "owner_reply": config.owner_reply,
        "notify": {
            "write_needs_owner": config.notify.write_needs_owner,
            "webhook_url": config.notify.webhook_url,
        },
        "run_dir": str(config.run_dir.relative_to(config.repo_root)),
        "developer_agent_id": config.developer_agent_id,
        "master_agent_id": config.master_agent_id,
        "last_iteration": config.last_iteration,
        "last_instruction": config.last_instruction,
    }
    if config.brief_file:
        data["brief_file"] = str(config.brief_file.relative_to(config.repo_root))
    config.config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
