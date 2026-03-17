"""REST API endpoints for UPS data."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from nut_up import __version__
from nut_up.descriptions import COMMANDS as CMD_DESCS, VARIABLES as VAR_DESCS
from nut_up.upsd_client import NUTError

router = APIRouter()


@router.get("/api/info")
async def get_info() -> dict:
    return {"version": __version__, "name": "nut-up"}


@router.get("/api/ups")
async def get_ups_list() -> dict:
    from nut_up.app import get_latest_ups_data

    return get_latest_ups_data()


@router.get("/api/ups/{name}")
async def get_ups(name: str) -> dict:
    from nut_up.app import get_latest_ups_data

    data = get_latest_ups_data()
    if name not in data:
        raise HTTPException(status_code=404, detail=f"UPS '{name}' not found")
    return data[name]


@router.get("/api/ups/{name}/history")
async def get_history(name: str):
    from nut_up.app import get_ups_history

    history = get_ups_history()
    if name not in history:
        return []
    return history[name]


@router.get("/api/ups/{name}/variables")
async def get_ups_variables(name: str) -> dict:
    from nut_up.app import get_upsd_client

    client = get_upsd_client()
    try:
        return await client.list_vars(name)
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/api/ups/{name}/rw")
async def get_ups_rw(name: str) -> dict:
    from nut_up.app import get_upsd_client

    client = get_upsd_client()
    try:
        return await client.list_rw(name)
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/api/ups/{name}/commands")
async def get_ups_commands(name: str) -> list:
    from nut_up.app import get_upsd_client

    client = get_upsd_client()
    try:
        return await client.list_commands(name)
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/api/descriptions")
async def get_descriptions() -> dict:
    """Return human-readable descriptions for known NUT variables and commands."""
    return {"variables": VAR_DESCS, "commands": CMD_DESCS}


@router.get("/api/ups/{name}/clients")
async def get_ups_clients(name: str) -> list:
    from nut_up.app import get_upsd_client

    client = get_upsd_client()
    try:
        return await client.list_clients(name)
    except NUTError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=503, detail=str(e))
