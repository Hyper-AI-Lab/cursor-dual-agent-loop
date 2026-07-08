#!/usr/bin/env bash
set -euo pipefail
DARKHERD="${DARKHERD_PATH:-../darkherd}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DH="$(cd "$DARKHERD" && pwd)"
cp -a "$SRC_ROOT/orchestrator/." "$DH/auto/orchestrator/"
cp -a "$SRC_ROOT/templates/auto/guidelines/." "$DH/auto/guidelines/"
cp -a "$SRC_ROOT/templates/.cursor/agents/." "$DH/.cursor/agents/"
cp -a "$SRC_ROOT/templates/.cursor/hooks/." "$DH/.cursor/hooks/"
cp "$SRC_ROOT/templates/.cursor/hooks.json" "$DH/.cursor/hooks.json"
cp "$SRC_ROOT/templates/auto/orchestrator/config.example.yaml" "$DH/auto/orchestrator/config.example.yaml"
cp "$SRC_ROOT/tests/test_dual_agent_orchestrator.py" "$DH/tests/" 2>/dev/null || true
echo "Synced to $DH"
