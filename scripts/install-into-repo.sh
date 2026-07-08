#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then echo "Usage: $0 /path/to/target-repo [--force]"; exit 1; fi
TARGET="$(cd "$1" && pwd)"
FORCE="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$TARGET/auto/orchestrator"
cp -a "$SRC/orchestrator/." "$TARGET/auto/orchestrator/"
echo "INSTALLED: auto/orchestrator/"
for rel in auto/__init__.py auto/guidelines auto/sandbox auto/runs .cursor/agents .cursor/hooks .cursor/hooks.json auto/orchestrator/config.example.yaml; do
  src="$SRC/templates/$rel"
  dst="$TARGET/$rel"
  if [[ ! -e "$src" ]]; then continue; fi
  if [[ -e "$dst" && "$FORCE" != "--force" ]]; then echo "SKIP: $rel"; continue; fi
  mkdir -p "$(dirname "$dst")"
  if [[ -d "$src" ]]; then mkdir -p "$dst"; cp -a "$src/." "$dst/"; else cp "$src" "$dst"; fi
  echo "INSTALLED: $rel"
done
chmod +x "$TARGET/.cursor/hooks/"*.sh 2>/dev/null || true
mkdir -p "$TARGET/auto/runs/hello-sandbox"
if [[ ! -f "$TARGET/auto/runs/hello-sandbox/config.yaml" ]]; then
  cp "$SRC/examples/hello-sandbox/config.yaml" "$TARGET/auto/runs/hello-sandbox/config.yaml"
fi
echo "Install complete."
