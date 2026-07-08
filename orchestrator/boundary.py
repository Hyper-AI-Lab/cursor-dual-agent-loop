"""Path allowlist helpers shared by hooks and tests."""

from __future__ import annotations

from pathlib import Path


def normalize_repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def path_is_allowed(
    repo_root: Path,
    target: str | Path,
    *,
    sandbox_dir: Path,
    allowed_paths: list[str],
) -> bool:
    resolved = normalize_repo_path(repo_root, target)
    repo_root = repo_root.resolve()
    sandbox_dir = sandbox_dir.resolve()

    try:
        resolved.relative_to(sandbox_dir)
        return True
    except ValueError:
        pass

    for rel in allowed_paths:
        allowed = normalize_repo_path(repo_root, rel)
        try:
            if allowed.is_dir():
                resolved.relative_to(allowed)
                return True
            if resolved == allowed:
                return True
        except ValueError:
            continue
    return False


def extract_tool_path(tool_name: str, tool_input: dict) -> str | None:
    if tool_name in {"Write", "Delete"}:
        for key in ("path", "file_path", "filePath", "target_file"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None
