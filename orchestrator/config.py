"""Load and validate dual-agent loop configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import hashlib
import yaml

BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"


@dataclass
class NotifyConfig:
    write_needs_owner: bool = True
    webhook_url: str | None = None


@dataclass
class LoopConfig:
    task_id: str
    task: str
    workspace: Path
    write_roots: list[str]
    master_instructions: Path
    task_file: Path | None
    model: str
    developer_model: str
    master_model: str
    backend: str
    max_iterations: int
    safety_mode: str
    safety_guidelines: Path
    escalate_policy: Path
    initial_instruction: str
    owner_reply: str | None
    notify: NotifyConfig
    run_dir: Path
    test_command: str | None = None
    lint_command: str | None = None
    developer_agent_id: str | None = None
    master_agent_id: str | None = None
    last_iteration: int = 0
    last_instruction: str | None = None
    last_developer_mode: str | None = None
    config_path: Path | None = None
    # Legacy aliases kept for internal helpers
    repo_root: Path = field(init=False)
    sandbox_dir: Path = field(init=False)
    allowed_paths: list[str] = field(init=False)
    master_guidelines: Path = field(init=False)
    developer_guidelines: Path = field(init=False)
    workspace_mode: str = "constrained"

    def __post_init__(self) -> None:
        self.repo_root = self.workspace
        self.sandbox_dir = self.workspace / "auto" / "sandbox"
        self.allowed_paths = list(self.write_roots)
        self.master_guidelines = self.master_instructions
        self.developer_guidelines = BUILTIN_DIR / "developer_protocol.md"

    @property
    def developer_cwd(self) -> Path:
        return self.workspace

    @property
    def state_scope_paths(self) -> list[str]:
        # Empty write_roots means whole workspace (".")
        roots = self.write_roots or ["."]
        if "." in roots or "" in roots:
            return ["."]
        return list(roots)


def _resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def _as_rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _load_text_file(path: Path) -> str:
    if not path.exists():
        raise ValueError(f"required file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _resolve_policy(workspace: Path, value: Any, default_name: str) -> Path:
    default = BUILTIN_DIR / default_name
    if value is None or value == "default":
        return default
    if isinstance(value, str) and value.strip():
        resolved = _resolve(workspace, value.strip())
        if resolved and resolved.exists():
            return resolved
        raise ValueError(f"policy file not found: {value}")
    return default


def load_config(config_path: Path) -> LoopConfig:
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    # Prefer workspace; accept legacy repo_root.
    # "." means the repo that contains auto/orchestrator/ (not the config file folder).
    workspace_raw = raw.get("workspace", raw.get("repo_root", "."))
    here = Path(__file__).resolve()
    # Installed layout: <repo>/auto/orchestrator/config.py
    # Public-repo layout: <repo>/orchestrator/config.py
    if here.parent.name == "orchestrator" and here.parents[1].name == "auto":
        module_repo = here.parents[2]
    else:
        module_repo = here.parents[1]

    if not workspace_raw or str(workspace_raw).strip() in (".", ""):
        workspace = module_repo
    else:
        workspace_path = Path(str(workspace_raw))
        if workspace_path.is_absolute():
            workspace = workspace_path.resolve()
        else:
            workspace = (module_repo / workspace_path).resolve()

    task_id = raw.get("task_id") or config_path.parent.name

    # Task: path (preferred) or inline string / brief_file legacy
    task_text = ""
    task_file: Path | None = None
    task_raw = raw.get("task")
    brief_file = _resolve(workspace, raw.get("brief_file"))
    if isinstance(task_raw, str) and task_raw.strip():
        candidate = _resolve(workspace, task_raw.strip())
        if candidate and candidate.exists() and candidate.is_file():
            task_file = candidate
            task_text = _load_text_file(candidate)
        else:
            # Inline task text (legacy / simple)
            task_text = task_raw.strip()
    if not task_text and brief_file and brief_file.exists():
        task_file = brief_file
        task_text = _load_text_file(brief_file)
    if not task_text:
        raise ValueError("config must define task (file path or inline text) or brief_file")

    master_raw = raw.get("master_instructions") or raw.get("master_guidelines")
    if not master_raw:
        master_instructions = BUILTIN_DIR / "master_protocol.md"
    else:
        master_instructions = _resolve(workspace, str(master_raw))
        if not master_instructions or not master_instructions.exists():
            raise ValueError(f"master_instructions not found: {master_raw}")

    write_roots_raw = raw.get("write_roots", raw.get("allowed_paths"))
    if write_roots_raw is None:
        write_roots = ["."]
    else:
        write_roots = [str(p) for p in write_roots_raw] or ["."]

    run_dir_raw = raw.get("run_dir")
    if run_dir_raw:
        run_dir = _resolve(workspace, run_dir_raw) or (workspace / "auto/runs" / task_id)
    else:
        run_dir = (workspace / "auto/runs" / task_id).resolve()

    raw_safety = raw.get("safety_mode", "off")
    if isinstance(raw_safety, bool):
        # YAML 1.1 may parse off/on as booleans
        safety_mode = "off" if raw_safety is False else "strict"
    else:
        safety_mode = str(raw_safety or "off").strip().lower()
    if safety_mode not in {"off", "soft", "strict"}:
        raise ValueError("safety_mode must be off, soft, or strict")

    safety_guidelines = _resolve_policy(
        workspace, raw.get("safety_guidelines"), "default_safety.md"
    )
    escalate_policy = _resolve_policy(
        workspace, raw.get("escalate_policy"), "default_escalate.md"
    )

    notify_raw = raw.get("notify") or {}
    notify = NotifyConfig(
        write_needs_owner=bool(notify_raw.get("write_needs_owner", True)),
        webhook_url=notify_raw.get("webhook_url"),
    )

    config = LoopConfig(
        task_id=task_id,
        task=task_text,
        workspace=workspace,
        write_roots=write_roots,
        master_instructions=master_instructions,
        task_file=task_file,
        model=str(raw.get("model", "auto") or "auto"),
        developer_model=str(
            raw.get("developer_model") or raw.get("model") or "auto"
        ),
        master_model=str(raw.get("master_model") or raw.get("model") or "auto"),
        backend=raw.get("backend", "sdk"),
        max_iterations=int(raw.get("max_iterations", 40)),
        safety_mode=safety_mode,
        safety_guidelines=safety_guidelines,
        escalate_policy=escalate_policy,
        initial_instruction=(raw.get("initial_instruction") or "").strip()
        or "Start with the first coherent step for this task.",
        owner_reply=(raw.get("owner_reply") or "").strip() or None,
        notify=notify,
        run_dir=run_dir,
        test_command=raw.get("test_command"),
        lint_command=raw.get("lint_command"),
        developer_agent_id=raw.get("developer_agent_id"),
        master_agent_id=raw.get("master_agent_id"),
        last_iteration=int(raw.get("last_iteration", 0)),
        last_instruction=raw.get("last_instruction"),
        last_developer_mode=(raw.get("last_developer_mode") or None),
        config_path=config_path.resolve(),
    )
    # Overlay durable runtime/resume state (does not rewrite owner config.yaml).
    state = load_runtime_state(run_dir)
    if state.get("developer_agent_id"):
        config.developer_agent_id = state.get("developer_agent_id")
    if state.get("master_agent_id"):
        config.master_agent_id = state.get("master_agent_id")
    if state.get("last_iteration") is not None:
        config.last_iteration = int(state.get("last_iteration") or 0)
    if "last_instruction" in state:
        config.last_instruction = state.get("last_instruction")
    if "last_developer_mode" in state:
        config.last_developer_mode = state.get("last_developer_mode")
    config.consumed_owner_reply_hash = state.get("consumed_owner_reply_hash")
    # If this owner_reply was already applied on a prior resume, do not re-inject.
    if config.owner_reply and config.consumed_owner_reply_hash == _owner_reply_hash(config.owner_reply):
        config.owner_reply = None
    return config




RUNTIME_STATE_KEYS = (
    "developer_agent_id",
    "master_agent_id",
    "last_iteration",
    "last_instruction",
    "last_developer_mode",
    "consumed_owner_reply_hash",
)


def _owner_reply_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def runtime_state_path(config: "LoopConfig") -> Path:
    return config.run_dir / "run_state.yaml"


def load_runtime_state(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "run_state.yaml"
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


def save_runtime_state(config: "LoopConfig") -> None:
    """Persist resume fields without rewriting the owner-edited config.yaml."""
    config.run_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "developer_agent_id": config.developer_agent_id,
        "master_agent_id": config.master_agent_id,
        "last_iteration": config.last_iteration,
        "last_instruction": config.last_instruction,
        "last_developer_mode": config.last_developer_mode,
        "consumed_owner_reply_hash": getattr(config, "consumed_owner_reply_hash", None),
    }
    runtime_state_path(config).write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def save_config(config: LoopConfig) -> None:
    """Backward-compatible name: only writes run_state.yaml (never clobbers config.yaml)."""
    if not config.config_path:
        raise ValueError("config_path is required to save")
    save_runtime_state(config)


def mark_owner_reply_consumed(config: LoopConfig, reply: str) -> None:
    config.consumed_owner_reply_hash = _owner_reply_hash(reply)
    config.owner_reply = None
    save_runtime_state(config)
