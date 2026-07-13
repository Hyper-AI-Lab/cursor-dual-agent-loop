# Contributing

Thanks for helping improve **cursor-dual-agent-loop**.

## Ways to help (high impact for discovery)

1. **Star** the repo if it is useful — GitHub ranking and topic browse both care.
2. Open issues for: install friction, unclear README wording, SDK/CLI breakage.
3. Send PRs that improve docs, examples, or tests (prefer small, focused diffs).
4. Mention the project in write-ups / lists about Cursor SDK, autonomous coding, or agent loops (with an honest caveat: needs `CURSOR_API_KEY` + CLI).

## Dev setup

```bash
pip install cursor-sdk pyyaml pytest
PYTHONPATH=. pytest tests/ -q
```

`auto/orchestrator` is a symlink to `./orchestrator` for the same import path used after `install-into-repo.sh`.

## PR checklist

- [ ] Tests pass (`pytest`)
- [ ] README / example docs updated if behavior changed
- [ ] No secrets committed

## Code of conduct

Be respectful. This project is MIT and community-friendly; hostile or spammy issues will be closed.
