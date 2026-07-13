# Default safety guidelines (soft)

Agents have broad permissions inside the workspace. Still follow these baseline rules:

- Never commit, print, or publish API keys, tokens, passwords, private keys, or `.env` secrets
- Never exfiltrate secrets to public remotes, paste sites, or third-party services
- Prefer local verification; treat production systems and real user data carefully
- If a step would expose secrets or cause irreversible external damage, stop and ESCALATE

The owner may replace this file via `safety_guidelines` in config.
