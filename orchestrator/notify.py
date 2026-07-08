"""Owner notifications for STOP, ESCALATE, and stuck loops."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def notify_owner(
    run_dir: Path,
    event: str,
    summary: str,
    *,
    write_needs_owner: bool = True,
    webhook_url: str | None = None,
    task_id: str = "",
) -> Path | None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "task_id": task_id,
        "utc_stamp": _utc_now(),
        "summary": summary,
    }

    path: Path | None = None
    if write_needs_owner:
        path = run_dir / "NEEDS_OWNER.md"
        body = (
            f"# Owner notification: {event}\n\n"
            f"- **Task:** {task_id}\n"
            f"- **Time (UTC):** {payload['utc_stamp']}\n\n"
            f"## Summary\n\n{summary}\n\n"
            f"## Resume\n\n"
            f"1. Add your reply to `owner_reply` in the task config.yaml\n"
            f"2. Run: `python auto/orchestrator/dual_agent_loop.py --config <config> --resume`\n"
        )
        path.write_text(body, encoding="utf-8")

    if webhook_url:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15):
                pass
        except urllib.error.URLError:
            fallback = run_dir / "webhook_failed.json"
            fallback.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return path
