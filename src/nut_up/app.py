"""FastAPI application factory and background polling."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from nut_up.state import StateManager
from nut_up.upsd_client import UpsdClient
from nut_up.ws import ConnectionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (set during lifespan)
# ---------------------------------------------------------------------------

_ws_manager: ConnectionManager | None = None
_upsd_client: UpsdClient | None = None
_state_manager: StateManager | None = None
_latest_ups_data: dict = {}


def get_ws_manager() -> ConnectionManager:
    assert _ws_manager is not None, "App not started"
    return _ws_manager


def get_upsd_client() -> UpsdClient:
    assert _upsd_client is not None, "App not started"
    return _upsd_client


def get_state_manager() -> StateManager:
    assert _state_manager is not None, "App not started"
    return _state_manager


def get_latest_ups_data() -> dict:
    return _latest_ups_data


# ---------------------------------------------------------------------------
# Background UPS polling
# ---------------------------------------------------------------------------

async def _poll_ups(client: UpsdClient, manager: ConnectionManager) -> None:
    """Poll all UPS devices every 2 seconds and broadcast via WebSocket."""
    global _latest_ups_data

    while True:
        try:
            ups_list = await client.list_ups()
            data: dict[str, dict] = {}

            for name, description in ups_list.items():
                variables = await client.list_vars(name)
                data[name] = {
                    "name": name,
                    "description": description,
                    "variables": variables,
                    "status": variables.get("ups.status", "unknown"),
                    "battery_charge": variables.get("battery.charge"),
                    "battery_runtime": variables.get("battery.runtime"),
                    "load": variables.get("ups.load"),
                    "input_voltage": variables.get("input.voltage"),
                    "output_voltage": variables.get("output.voltage"),
                }

            _latest_ups_data = data
            await manager.broadcast({"type": "ups_data", "data": data})

        except Exception as e:
            logger.error("UPS poll error: %s", e)
            await manager.broadcast({"type": "error", "message": str(e)})

            # Close and reconnect after a delay
            try:
                await client.close()
            except Exception:
                pass

            await asyncio.sleep(5)

            try:
                client._reader, client._writer = await asyncio.open_connection(
                    client.host, client.port
                )
            except Exception as reconnect_err:
                logger.error("Reconnect failed: %s", reconnect_err)

        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ws_manager, _upsd_client, _state_manager

    _ws_manager = ConnectionManager()

    state_file = Path(os.environ.get("NUT_UP_STATE_FILE", "/var/lib/nut-up/state.json"))
    _state_manager = StateManager(state_file)

    upsd_host = os.environ.get("NUT_UP_UPSD_HOST", "localhost")
    upsd_port = int(os.environ.get("NUT_UP_UPSD_PORT", "3493"))
    _upsd_client = UpsdClient(upsd_host, upsd_port)

    poll_task = None
    try:
        await _upsd_client.__aenter__()
        poll_task = asyncio.create_task(_poll_ups(_upsd_client, _ws_manager))
    except (OSError, ConnectionRefusedError) as e:
        logger.warning("Could not connect to upsd at %s:%s: %s", upsd_host, upsd_port, e)

    yield

    if poll_task is not None:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass

    if _upsd_client is not None:
        try:
            await _upsd_client.close()
        except Exception:
            pass

    _ws_manager = None
    _upsd_client = None
    _state_manager = None


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="nut-up", lifespan=lifespan)

    from nut_up.routers import api, commands, enrollment, ws

    app.include_router(api.router)
    app.include_router(commands.router)
    app.include_router(enrollment.router)
    app.include_router(ws.router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
