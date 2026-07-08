# hello-sandbox smoke test

Runnable end-to-end check that the dual-agent loop works on your machine.

**You need:** Cursor account, `CURSOR_API_KEY`, Python 3.10+, `cursor-sdk`, Cursor CLI (`agent`).

## 1. Install into a project

Use any empty or existing git repo as the target:

```bash
git clone https://github.com/Hyper-AI-Lab/cursor-dual-agent-loop.git
./cursor-dual-agent-loop/scripts/install-into-repo.sh /path/to/your-project
```

## 2. Prepare environment

```bash
cd /path/to/your-project

# Optional but recommended: isolated Python env
conda create -n dual-agent python=3.12 -y
conda activate dual-agent

pip install cursor-sdk pyyaml pytest
curl https://cursor.com/install -fsS | bash
export PATH="$HOME/.local/bin:$PATH"
export CURSOR_API_KEY="cursor_..."   # Cursor Dashboard -> Integrations / API Keys

python auto/orchestrator/verify_prereqs.py
# Expect: OK: CLI, OK: cursor-sdk, OK: Agent.prompt replied
```

## 3. Install smoke-test config

```bash
mkdir -p auto/runs/hello-sandbox
cp /path/to/cursor-dual-agent-loop/examples/hello-sandbox/config.yaml \
   auto/runs/hello-sandbox/config.yaml
```

Or copy from `auto/orchestrator/config.example.yaml` after install (same task).

**Model:** set `model: auto` in config.yaml to use Cursor Auto routing, or pin e.g. `composer-2.5`.

## 4. Run the loop

```bash
python auto/orchestrator/dual_agent_loop.py \
  --config auto/runs/hello-sandbox/config.yaml \
  --backend sdk
```

### Expected behavior (2 iterations typical)

| Iteration | Master decision | What happened |
|-----------|-----------------|---------------|
| 1 | `FIX` | Developer created `hello.py`; master asks for pytest tests |
| 2 | `STOP` | Tests added, pytest passed — done |

`FIX` is normal — it means "not finished yet", not a crash.

## 5. Verify output

```bash
ls auto/sandbox/
PYTHONPATH=. pytest auto/sandbox/test_hello.py -q
# 2 passed

tail auto/runs/hello-sandbox/master.log
```

Compare with reference files in `examples/hello-sandbox/reference/` (expected end state).

## 6. After the run (your choice)

The loop does **not** commit. For a smoke test you can:

- **Discard** (reset sandbox): `git checkout -- auto/sandbox/ 2>/dev/null; rm -f auto/sandbox/*.py`
- **Keep** (record success): `git add auto/sandbox/*.py && git commit -m "hello-sandbox smoke test"`
- On **STOP**, read `auto/runs/hello-sandbox/COMPLETE.md` (summary only; no resume needed)

## Run in background (screen)

```bash
screen -S dual-agent-hello
python auto/orchestrator/dual_agent_loop.py --config auto/runs/hello-sandbox/config.yaml --backend sdk
# Ctrl+A, D to detach
tail -f auto/runs/hello-sandbox/master.log
```
