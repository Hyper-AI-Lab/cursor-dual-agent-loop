# Default escalate policy

Return **ESCALATE** (and stop the loop for the owner) when any of these apply:

- Product intent, architecture trade-off, or conflicting requirements need a human choice
- Security, privacy, legal, payment, or compliance judgment is required
- Production deploy, irreversible data deletion, or credential/secret rotation is requested
- The developer is blocked by missing credentials, external access, or owner-only decisions
- The task instructions are contradictory or incomplete in a way you cannot safely resolve

Do **not** escalate merely to ask for confirmation of a clear next step.
