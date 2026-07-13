# Loop-run setup assistant

**For the human:** Open a Cursor agent chat and say:

> Read `auto/runs/SETUP_LOOP_RUN.md` and help me set up a dual-agent loop run.

**For the agent:** Interview briefly, then create a minimal `config.yaml` plus ensure the
two instruction files exist. **Do not start the loop** unless the user asks.

## What the user must provide

1. **workspace** — directory (usually `.` = this repo)
2. **model** — e.g. `auto`
3. **max_iterations** — hard stop (user force-stops anytime with Ctrl+C)
4. **master_instructions** — path to File 1 (master context)
5. **task** — path to File 2 (goal / how master should drive the developer)

Everything else has defaults. See `auto/orchestrator/config.example.yaml`.

## Interview (short)

Ask for: task_id, workspace, model, max_iterations, paths to the two files,
optional write_roots (default `.`), optional safety_mode (default `"off"`).

Confirm a summary, then write:

```
auto/runs/<task-id>/config.yaml
```

Point `master_instructions` and `task` at the user's two files (copy into the run
dir if needed).

## Built-in (do not ask the user to invent these)

- DECISION: CONTINUE | FIX | STOP | ESCALATE protocol
- Default escalate policy
- Default soft safety guidelines (no secret leakage)
- Invalid/missing DECISION → stop + NEEDS_OWNER.md

## Launch handoff

```bash
conda activate dual-agent
export PATH="$HOME/.local/bin:$PATH"
cd <workspace>
screen -S <task-id>
python auto/orchestrator/dual_agent_loop.py --config auto/runs/<task-id>/config.yaml --backend sdk
```

Monitor: `developer.log`, `master.log`, `COMPLETE.md`, `NEEDS_OWNER.md`.
