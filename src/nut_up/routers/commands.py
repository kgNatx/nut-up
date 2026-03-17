"""Command execution and variable write endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nut_up.upsd_client import NUTError, UpsdClient

router = APIRouter()


class CommandRequest(BaseModel):
    command: str


class SetVariableRequest(BaseModel):
    variable: str
    value: str


async def _get_authed_client() -> UpsdClient:
    """Create a new authenticated UpsdClient connection using admin credentials from state."""
    from nut_up.app import get_state_manager, get_upsd_client

    state = get_state_manager()
    data = state.load()
    server = data.get("server", {})
    admin_password = server.get("admin_password")
    if not admin_password:
        raise HTTPException(status_code=500, detail="Admin password not configured in state")

    # Get host/port from the existing client
    existing = get_upsd_client()
    client = UpsdClient(existing.host, existing.port)
    await client.__aenter__()
    await client.authenticate("admin", admin_password)
    return client


@router.post("/api/ups/{name}/command")
async def run_command(name: str, body: CommandRequest) -> dict:
    client = await _get_authed_client()
    try:
        await client.run_command(name, body.command)
        return {"status": "ok"}
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()


@router.post("/api/ups/{name}/variable")
async def set_variable(name: str, body: SetVariableRequest) -> dict:
    client = await _get_authed_client()
    try:
        await client.set_var(name, body.variable, body.value)
        return {"status": "ok", "variable": body.variable, "value": body.value}
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()
