#!/usr/bin/env bash
set -euo pipefail
DARKHERD="${DARKHERD_PATH:-../darkherd}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DH="$(cd "$DARKHERD" && pwd)"
cp -a "$DH/auto/orchestrator/." "$SRC_ROOT/orchestrator/"
cp -a "$DH/auto/guidelines/." "$SRC_ROOT/templates/auto/guidelines/"
cp -a "$DH/.cursor/agents/." "$SRC_ROOT/templates/.cursor/agents/"
cp -a "$DH/.cursor/hooks/." "$SRC_ROOT/templates/.cursor/hooks/"
cp "$DH/.cursor/hooks.json" "$SRC_ROOT/templates/.cursor/hooks.json"
cp "$DH/auto/orchestrator/config.example.yaml" "$SRC_ROOT/templates/auto/orchestrator/config.example.yaml"
cp "$DH/tests/test_dual_agent_orchestrator.py" "$SRC_ROOT/tests/" 2>/dev/null || true
echo "Synced from $DH"
