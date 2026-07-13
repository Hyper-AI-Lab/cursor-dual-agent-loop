# hello-sandbox smoke test

Runnable end-to-end check that the dual-agent loop works on your machine.

**You need:** Cursor account, `CURSOR_API_KEY`, Python 3.10+, `cursor-sdk`, Cursor CLI (`agent`).

This example uses the **same config shape** as a real run: `config.yaml` plus two instruction files.

| File | Role |
|------|------|
| `config.yaml` | workspace, model(s), `max_iterations`, paths, safety |
| `instruction_for_master` | File 1 — how the master should supervise |
| `instruction_for_master_to_guide_developer` | File 2 — the task / acceptance criteria |

## 1. Install into a project

```bash
git clone https://github.com/Hyper-AI-Lab/cursor-dual-agent-loop.git
./cursor-dual-agent-loop/scripts/install-into-repo.sh /path/to/your-project
```

The installer copies orchestrator code and, if missing, seeds `auto/runs/hello-sandbox/` with this example’s config + instruction files.

## 2. Prepare environment

```bash
cd /path/to/your-project

conda create -n dual-agent python=3.12 -y   # optional
conda activate dual-agent

pip install cursor-sdk pyyaml pytest
curl https://cursor.com/install -fsS | bash
export PATH="$HOME/.local/bin:$PATH"
export CURSOR_API_KEY="cursor_..."

python auto/orchestrator/verify_prereqs.py
```

## 3. Confirm run files

```bash
ls auto/runs/hello-sandbox/
# config.yaml
# instruction_for_master
# instruction_for_master_to_guide_developer
```

If you installed an older copy, refresh from this example:

```bash
cp /path/to/cursor-dual-agent-loop/examples/hello-sandbox/config.yaml \
   auto/runs/hello-sandbox/config.yaml
cp /path/to/cursor-dual-agent-loop/examples/hello-sandbox/instruction_for_master \
   auto/runs/hello-sandbox/instruction_for_master
cp /path/to/cursor-dual-agent-loop/examples/hello-sandbox/instruction_for_master_to_guide_developer \
   auto/runs/hello-sandbox/instruction_for_master_to_guide_developer
```

Optional: set `developer_model` / `master_model` in `config.yaml` to split cost (cheaper/`auto` developer, stronger master).

## 4. Run the loop

```bash
python auto/orchestrator/dual_agent_loop.py \
  --config auto/runs/hello-sandbox/config.yaml \
  --backend sdk
```

### Expected behavior (a few iterations typical)

| Master decision | Meaning |
|-----------------|---------|
| `CONTINUE` / `FIX` | More work needed (FIX is normal, not a crash) |
| `STOP` | Acceptance criteria met → `COMPLETE.md` |

## 5. Verify output

```bash
ls auto/sandbox/
PYTHONPATH=. pytest auto/sandbox/test_hello.py -q
tail auto/runs/hello-sandbox/master.log
```

Compare with `examples/hello-sandbox/reference/` (expected end state).

## 6. After the run

The loop does **not** commit. For a smoke test you can:

- **Discard:** `rm -f auto/sandbox/hello.py auto/sandbox/test_hello.py`
- **Keep:** `git add auto/sandbox/*.py && git commit -m "hello-sandbox smoke test"`
- On **STOP**, read `auto/runs/hello-sandbox/COMPLETE.md`

## Background (screen)

```bash
screen -S dual-agent-hello
python auto/orchestrator/dual_agent_loop.py --config auto/runs/hello-sandbox/config.yaml --backend sdk
# Ctrl+A, D to detach
tail -f auto/runs/hello-sandbox/master.log
```
