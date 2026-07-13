"""SDK backend for dual-agent loop."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, AsyncClient, CursorAgentError, LocalAgentOptions, SendOptions


@dataclass
class SdkAgents:
    client: AsyncClient
    developer: object
    master: object


async def create_sdk_agents(
    *,
    repo_root: Path,
    developer_cwd: Path,
    model: str,
    developer_model: str | None = None,
    master_model: str | None = None,
    developer_agent_id: str | None = None,
    master_agent_id: str | None = None,
) -> SdkAgents:
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise CursorAgentError("CURSOR_API_KEY is not set")

    dev_model = developer_model or model
    mst_model = master_model or model

    client = await AsyncClient.launch_bridge(workspace=str(repo_root))

    local_dev = LocalAgentOptions(cwd=str(developer_cwd), setting_sources=["project"])
    local_master = LocalAgentOptions(cwd=str(repo_root), setting_sources=["project"])

    if developer_agent_id:
        developer = await client.resume_agent(
            developer_agent_id,
            AgentOptions(api_key=api_key, model=dev_model, local=local_dev),
        )
    else:
        developer = await client.create_agent(
            name="developer",
            model=dev_model,
            api_key=api_key,
            local=local_dev,
        )

    if master_agent_id:
        master = await client.resume_agent(
            master_agent_id,
            AgentOptions(api_key=api_key, model=mst_model, local=local_master),
        )
    else:
        master = await client.create_agent(
            name="master",
            model=mst_model,
            api_key=api_key,
            local=local_master,
        )

    return SdkAgents(client=client, developer=developer, master=master)


async def send_developer(
    agents: SdkAgents, prompt: str, *, mode: str | None = None
) -> str:
    """Send to developer. mode=None|agent -> agent mode; mode=plan -> Plan Mode."""
    if mode and mode.lower() == "plan":
        run = await agents.developer.send(prompt, SendOptions(mode="plan"))
    else:
        run = await agents.developer.send(prompt)
    result = await run.wait()
    if result.status == "error":
        raise RuntimeError(f"developer run failed: {getattr(result, 'id', 'unknown')}")
    return (await run.text()).strip()


async def send_master(agents: SdkAgents, prompt: str, *, mode: str | None = None) -> str:
    """Send to master. Default agent mode so replies include full DECISION blocks.

    Pass mode="plan" only if you explicitly want Plan Mode (often returns short
    planning status text without DECISION: CONTINUE|FIX|STOP|ESCALATE).
    """
    if mode:
        run = await agents.master.send(prompt, SendOptions(mode=mode))
    else:
        run = await agents.master.send(prompt)
    result = await run.wait()
    if result.status == "error":
        raise RuntimeError(f"master run failed: {getattr(result, 'id', 'unknown')}")
    return (await run.text()).strip()


async def close_sdk_agents(agents: SdkAgents) -> tuple[str | None, str | None]:
    dev_id = getattr(agents.developer, "agent_id", None)
    master_id = getattr(agents.master, "agent_id", None)
    await agents.developer.close()
    await agents.master.close()
    await agents.client.aclose()
    return dev_id, master_id


def sync_prompt(prompt: str, *, cwd: Path, model: str) -> str:
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise CursorAgentError("CURSOR_API_KEY is not set")
    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(cwd), setting_sources=["project"]),
        ),
    )
    if result.status == "error":
        raise RuntimeError(f"agent prompt failed: {getattr(result, 'id', 'unknown')}")
    return (result.result or "").strip()
