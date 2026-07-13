# cursor-dual-agent-loop

Headless **master + developer** autonomous loop for [Cursor](https://cursor.com) CLI and Python SDK.

A Python orchestrator alternates two Cursor agents:

1. **Developer** — implements one step, verifies, reports structured output.
2. **Master** — reviews artifacts/output and returns `CONTINUE`, `FIX`, `STOP`, or `ESCALATE`.

> **Requires:** Cursor account, `CURSOR_API_KEY`, Cursor CLI, and `cursor-sdk`.  
> Not affiliated with Cursor Inc. See [Hyper AI Lab](https://hyperailab.com/).

## What you provide

In `config.yaml`:

| Field | Meaning |
|-------|---------|
| `workspace` | Directory agents work in (default `.`) |
| `model` | e.g. `auto` |
| `max_iterations` | Hard stop budget |
| `master_instructions` | File 1 — master context / how to think |
| `task` | File 2 (path) or inline text — goal the master uses to drive the developer |

Optional: `write_roots` (default whole workspace), `safety_mode` (`"off"` default), `run_dir`, `backend`.

Built-in (not user homework): DECISION protocol, escalate policy, soft safety guidelines.
Force-stop anytime with `Ctrl+C`.

## Loop sequence

1. **Bootstrap 1** — Master reads `master_instructions` (File 1), replies `READY`
2. **Bootstrap 2** — Master reads `task` (File 2), returns first `DECISION` + `INSTRUCTION_FOR_DEVELOPER`
3. **Loop** — Developer → Master review → next instruction, until STOP / ESCALATE / max_iterations

## Smoke test (recommended first run)

See **[examples/hello-sandbox/README.md](examples/hello-sandbox/README.md)**.

Architecture: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Quick install into your repo

```bash
git clone https://github.com/Hyper-AI-Lab/cursor-dual-agent-loop.git
./cursor-dual-agent-loop/scripts/install-into-repo.sh /path/to/your-project

cd /path/to/your-project
export CURSOR_API_KEY="cursor_..."
pip install cursor-sdk pyyaml
curl https://cursor.com/install -fsS | bash
python auto/orchestrator/verify_prereqs.py

python auto/orchestrator/dual_agent_loop.py \
  --config auto/runs/hello-sandbox/config.yaml \
  --backend sdk
```

## Minimal config example

```yaml
task_id: my-task
workspace: .
model: auto
max_iterations: 40
backend: sdk
write_roots: ["."]
safety_mode: "off"
master_instructions: path/to/instruction_for_master.md
task: path/to/task_for_developer.md
```

See `orchestrator/config.example.yaml` / `templates/auto/orchestrator/config.example.yaml`.

## Safety

- `safety_mode: "off"` / `soft` (default off): no hard shell denylist; soft rules from `safety_guidelines` (do not leak secrets).
- `safety_mode: strict`: hard-block a short denylist (`git push`, `rm -rf /`, …).
- `write_roots` bounds Write/Delete.

## Monitor / stop / resume

| Action | How |
|--------|-----|
| Monitor | `tail -f auto/runs/<task>/master.log` |
| Stop | `Ctrl+C` or kill orchestrator / screen session |
| Resume | Add `owner_reply` to config, run with `--resume` |

Invalid/missing `DECISION:` lines also stop and write `NEEDS_OWNER.md`.

See [SYNC.md](SYNC.md) for maintainer sync.

## Development (this repo)

```bash
pip install cursor-sdk pyyaml pytest
# auto/orchestrator is a symlink to ./orchestrator for imports
PYTHONPATH=. pytest tests/ -q
```

## License

MIT — Copyright (c) 2026 Hyper-AI-Lab
