# cursor-dual-agent-loop

Headless **master + developer** autonomous loop for [Cursor](https://cursor.com) CLI and Python SDK.

A Python orchestrator alternates two Cursor agents:

1. **Developer** — implements one step, runs verification, reports structured output.
2. **Master** — reviews diff/tests and returns `CONTINUE`, `FIX`, `STOP`, or `ESCALATE`.

Sandbox hooks restrict file writes to `auto/sandbox/` plus configurable `allowed_paths`.

> **Requires:** Cursor account, `CURSOR_API_KEY`, Cursor CLI, and `cursor-sdk`.  
> Not affiliated with Cursor Inc. See [Hyper AI Lab](https://hyperailab.com/).

## Quick install into your repo

```bash
git clone https://github.com/Hyper-AI-Lab/cursor-dual-agent-loop.git
./cursor-dual-agent-loop/scripts/install-into-repo.sh /path/to/your-project

cd /path/to/your-project
export CURSOR_API_KEY="cursor_..."   # from Cursor Dashboard -> Integrations
pip install cursor-sdk pyyaml
curl https://cursor.com/install -fsS | bash
python auto/orchestrator/verify_prereqs.py

python auto/orchestrator/dual_agent_loop.py \
  --config auto/runs/hello-sandbox/config.yaml \
  --backend sdk
```

## Layout after install

```
your-project/
  auto/orchestrator/     # Python orchestrator
  auto/guidelines/       # Master/developer policy
  auto/sandbox/          # Developer workspace
  auto/runs/<task>/      # Per-task config + logs
  .cursor/agents/        # Cursor agent roles
  .cursor/hooks/         # Sandbox + shell safety
```

## Configuration

Copy `auto/orchestrator/config.example.yaml` to `auto/runs/my-task/config.yaml`.

Key fields: `task`, `test_command`, `allowed_paths`, `max_iterations`, `backend` (`sdk` or `cli`).

## Monitor / stop / resume

| Action | How |
|--------|-----|
| Monitor | `tail -f auto/runs/<task>/master.log` |
| Stop | `Ctrl+C` or kill orchestrator PID |
| Resume after ESCALATE | Add `owner_reply` to config, run with `--resume` |

See [SYNC.md](SYNC.md) for maintainer sync with downstream projects.

## Development (this repo)

```bash
pip install cursor-sdk pyyaml pytest
PYTHONPATH=. pytest tests/ -q
```

## License

MIT — Copyright (c) 2026 Hyper-AI-Lab
