#!/usr/bin/env bash
# Deny Write/Delete outside configured write_roots. Reads .cursor/hooks/allowlist.json.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"tool_name\",\"\"))")
tool_input=$(echo "$input" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin).get(\"tool_input\") or {}))")
cwd=$(echo "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get(\"cwd\") or \".\")")

python3 - "$tool_name" "$tool_input" "$cwd" <<'ENDPY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[3]).resolve()
tool_name = sys.argv[1]
tool_input = json.loads(sys.argv[2])

allowlist_path = repo_root / ".cursor" / "hooks" / "allowlist.json"
if not allowlist_path.exists():
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
sandbox_dir = (repo_root / allowlist.get("sandbox_dir", "auto/sandbox")).resolve()
write_roots = list(allowlist.get("write_roots") or allowlist.get("allowed_paths") or ["."])

sys.path.insert(0, str(repo_root))
from auto.orchestrator.boundary import extract_tool_path, path_is_allowed

if tool_name not in {"Write", "Delete"}:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

target = extract_tool_path(tool_name, tool_input)
if not target:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

if path_is_allowed(
    repo_root,
    target,
    sandbox_dir=sandbox_dir,
    write_roots=write_roots,
):
    print(json.dumps({"permission": "allow"}))
else:
    print(json.dumps({
        "permission": "deny",
        "user_message": f"Blocked edit outside write_roots: {target}",
        "agent_message": (
            f"Edits are restricted to write_roots={write_roots}. "
            f"Path not allowed: {target}"
        ),
    }))
ENDPY
