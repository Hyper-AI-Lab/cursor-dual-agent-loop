# Why this exists

## The Cursor quota paradox

Cursor users often have **more Auto / agent capacity than they can productively spend**.

The bottleneck is not usually “the model is too weak.” It is **process**:

1. You start an agent on a bounded task.
2. You wait, skim the diff, re-prompt, approve the next step.
3. You context-switch to meetings / other code.
4. The session stalls. Quota that could have shipped a small feature sits unused.

Fully unattended single-agent runs flip the problem: drift, shallow verification, early “done,” or risky edits.

## Design goal

**Spend quota on supervised progress**, not on human click-through.

Keep the human for:

- choosing the task and write boundary
- answering true product/security judgments (`ESCALATE`)
- reviewing `COMPLETE.md` / the final diff

Remove the human from:

- “looks fine, continue”
- “tests failed, fix that”
- “do the next phase of the same plan”

## How integrity is kept without babysitting

| Mechanism | Role |
|-----------|------|
| Master agent | Owns plan, acceptance, CONTINUE/FIX/STOP/ESCALATE |
| Artifact review | Master is instructed to inspect files/diffs, not trust prose |
| Structured decisions | Orchestrator only continues on explicit `DECISION:` lines |
| Write roots + hooks | Bound where agents may edit |
| Escalation policy | Force owner input when the task needs judgment |
| Hard-stop (`max_iterations`) | Process safety valve — **not** a completion budget leaked to the master |

## What this is not

- Not a replacement for CI, code review, or production change control
- Not affiliated with Cursor Inc.
- Not a giant agent platform — intentionally small and installable into an existing repo

## Cost asymmetry (strong master, cheap developer)

Most loop cost is **developer turns** (implement / verify). Master turns are fewer but decide quality.

Recommended pattern:

- **Master** → larger / more capable (often more expensive) model for review integrity  
- **Developer** → `auto` or a cheaper model for volume  

Configure with `master_model` and `developer_model` (both fall back to `model`).

