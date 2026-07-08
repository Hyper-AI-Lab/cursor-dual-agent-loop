#!/usr/bin/env bash
# Block destructive or deployment shell commands during autonomous loops.
set -euo pipefail

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; print(json.load(sys.stdin).get('command') or '')")

deny_patterns='rm -rf|git push|git reset --hard|docker compose up|docker-compose up|DROP TABLE|TRUNCATE '

if echo "$command" | grep -Eiq "$deny_patterns"; then
  python3 -c 'import json; print(json.dumps({"permission":"deny","user_message":"Destructive or deployment command blocked by dual-agent hook","agent_message":"This shell command is blocked in autonomous mode. Use local verification only."}))'
  exit 0
fi

echo '{"permission":"allow"}'
