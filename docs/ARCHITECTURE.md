# Architecture

## Three components (not two)

```
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (plain Python — dual_agent_loop.py)           │
│  Not an AI. No Cursor UI. Schedules turns, parses output.   │
└───────────────┬─────────────────────────────┬─────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│  DEVELOPER (Cursor agent) │   │  MASTER (Cursor agent)    │
│  Headless via SDK or CLI  │   │  Headless via SDK or CLI  │
│  Edits files, runs tests  │   │  Reviews, decides next    │
└───────────────────────────┘   └───────────────────────────┘
```

## Common misconceptions

| Myth | Reality |
|------|---------|
| Developer = Cursor desktop UI | **No.** Developer runs headless on your server via `cursor-sdk` or `agent -p`. Same agent engine as the IDE; no GUI required. |
| Orchestrator = CLI agent | **No.** Orchestrator is a Python script **you** run. It calls Cursor agents programmatically. |
| Master = you in the chat | **No.** Master is a second Cursor agent with a supervisor prompt. |
| You must reply each iteration | **No.** Orchestrator passes master instructions to the developer automatically. |

## One iteration

1. Orchestrator sends instruction → **Developer agent** (SDK `agent.send()` or CLI).
2. Developer edits `auto/sandbox/`, runs commands, returns structured report.
3. Orchestrator collects `git diff` + pytest output.
4. Orchestrator sends report + diff → **Master agent**.
5. Master returns `CONTINUE`, `FIX`, `STOP`, or `ESCALATE`.
6. If not `STOP`/`ESCALATE`, loop continues with new instruction.

## What runs on your machine

| Process | Technology |
|---------|------------|
| `dual_agent_loop.py` | Your Python interpreter |
| Developer / Master | Cursor local agent runtime (started by SDK bridge or CLI) |
| File edits | Real files on disk in your repo |
| Hooks | `.cursor/hooks/` enforce sandbox boundaries |

The Cursor **desktop app** is optional and not used in this headless setup.
