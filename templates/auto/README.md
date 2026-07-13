# Dual-agent autonomous development loop

Headless master/developer loop using the Cursor CLI / Python SDK.

## What you provide

In a run `config.yaml`:

1. **workspace** — directory agents work in (default `.` = this repo)
2. **model** — e.g. `auto`
3. **max_iterations** — hard stop budget
4. **master_instructions** — file: master context / how to think
5. **task** — file (or inline text): goal the master uses to drive the developer

Optional overrides (have defaults): `write_roots`, `safety_mode`, `safety_guidelines`,
`escalate_policy`, `run_dir`, `backend`, `owner_reply`.

Built-in (not user homework): DECISION protocol, escalate rules, soft safety text.
Force-stop anytime with Ctrl+C (or kill the `screen` session). Watch `*.log` under the run dir.

## Prerequisites

```bash
curl https://cursor.com/install -fsS | bash
pip install cursor-sdk pyyaml
export CURSOR_API_KEY="cursor_..."
python auto/orchestrator/verify_prereqs.py
```

## Minimal config

See `auto/orchestrator/config.example.yaml` and `auto/runs/explore_1/config.yaml`.

```yaml
task_id: explore_1
workspace: .
model: auto
max_iterations: 40
backend: sdk
write_roots: ["."]
safety_mode: "off"
master_instructions: auto/runs/explore_1/instruction_for_master
task: auto/runs/explore_1/instruction_for_master_to_guide_developer
```

## Launch

```bash
conda activate dual-agent
export PATH="$HOME/.local/bin:$PATH"

python auto/orchestrator/dual_agent_loop.py \
  --config auto/runs/explore_1/config.yaml \
  --backend sdk
```

## Resume after ESCALATE / invalid decision

1. On **STOP**: read `COMPLETE.md`
2. On **ESCALATE** / invalid decision / max_iterations: read `NEEDS_OWNER.md`
3. Add `owner_reply` to config and run with `--resume`

## Safety

- `safety_mode: "off"` (default) / `soft`: no hard shell denylist; soft rules come from
  `safety_guidelines` (default built-in: do not leak secrets/API keys).
- `safety_mode: strict`: hard-block a short denylist (`git push`, `rm -rf /`, …).
- `write_roots` still bounds Write/Delete (default: whole workspace).

## Layout

| Path | Role |
|------|------|
| `auto/orchestrator/dual_agent_loop.py` | Orchestrator (dumb plumbing) |
| `auto/orchestrator/builtin/` | Built-in protocol + default policies |
| `auto/runs/<task-id>/` | Per-task config, logs, notifications |
| `auto/runs/SETUP_LOOP_RUN.md` | Optional AI-assisted setup guide |
| `.cursor/hooks/` | Write boundary + optional strict shell blocks |
