"""Path allowlist helpers shared by hooks and tests."""

from __future__ import annotations

from pathlib import Path

# Always writable for run scaffolding/logs even when write_roots is narrowed.
IMPLICIT_ALLOWED_PATHS = ("auto/runs",)


def normalize_repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return child == parent


def path_is_allowed(
    repo_root: Path,
    target: str | Path,
    *,
    sandbox_dir: Path | None = None,
    allowed_paths: list[str] | None = None,
    write_roots: list[str] | None = None,
) -> bool:
    resolved = normalize_repo_path(repo_root, target)
    repo_root = repo_root.resolve()

    if sandbox_dir is not None and _under(resolved, sandbox_dir.resolve()):
        return True

    roots = list(write_roots if write_roots is not None else (allowed_paths or []))

    # Whole workspace
    if not roots or "." in roots or "" in roots:
        return _under(resolved, repo_root)

    for rel in (*IMPLICIT_ALLOWED_PATHS, *roots):
        allowed = normalize_repo_path(repo_root, rel)
        if _under(resolved, allowed) or resolved == allowed:
            return True
    return False


def extract_tool_path(tool_name: str, tool_input: dict) -> str | None:
    if tool_name in {"Write", "Delete"}:
        for key in ("path", "file_path", "filePath", "target_file"):
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None
