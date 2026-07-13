#!/usr/bin/env bash
# Optional hard blocks for destructive shell commands.
# Controlled by safety_mode in .cursor/hooks/allowlist.json (default: off).
set -euo pipefail

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get(\"command\") or \"\")")
cwd=$(echo "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get(\"cwd\") or \".\")")

python3 - "$command" "$cwd" <<'ENDPY'
import json
import re
import sys
from pathlib import Path

command = sys.argv[1]
cwd = Path(sys.argv[2]).resolve()

allowlist_path = cwd / ".cursor" / "hooks" / "allowlist.json"
safety_mode = "off"
if allowlist_path.exists():
    try:
        safety_mode = json.loads(allowlist_path.read_text(encoding="utf-8")).get("safety_mode", "off")
    except Exception:
        safety_mode = "off"
safety_mode = (safety_mode or "off").lower()

if safety_mode in {"off", "soft"}:
    print(json.dumps({"permission": "allow"}))
    raise SystemExit(0)

deny_patterns = [
    r"\brm\s+-rf\s+[/~]",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bdocker\s+compose\s+up\b",
    r"\bdocker-compose\s+up\b",
    r"\bDROP\s+TABLE\b",
    r"\bTRUNCATE\b",
]
if any(re.search(p, command, flags=re.I) for p in deny_patterns):
    print(json.dumps({
        "permission": "deny",
        "user_message": "Destructive command blocked (safety_mode=strict)",
        "agent_message": (
            "This shell command is blocked when safety_mode=strict. "
            "Set safety_mode to off or soft to allow, or choose a safer command."
        ),
    }))
else:
    print(json.dumps({"permission": "allow"}))
ENDPY
