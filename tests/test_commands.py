"""Tests for command execution and variable write endpoints."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

import nut_up.app as app_module
from nut_up.state import StateManager
from nut_up.upsd_client import UpsdClient
from nut_up.ws import ConnectionManager


@pytest.fixture
def env_setup(tmp_path, monkeypatch):
    """Seed state.json with server config including admin_password."""
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "keys": {},
                "clients": {},
                "server": {
                    "mode": "netserver",
                    "ups_name": "myups",
                    "admin_password": "testpass",
                    "monitor_password": "monpass",
                },
            }
        )
    )
    monkeypatch.setenv("NUT_UP_STATE_FILE", str(state_file))
    monkeypatch.setenv("NUT_UP_UPSD_HOST", "127.0.0.1")
    return state_file


@pytest.fixture
async def app_with_upsd(env_setup, mock_upsd, monkeypatch):
    """Create the app with module-level singletons pre-configured."""
    monkeypatch.setenv("NUT_UP_UPSD_PORT", str(mock_upsd.port))

    # Set module-level singletons so endpoints work without lifespan
    monkeypatch.setattr(app_module, "_ws_manager", ConnectionManager())
    monkeypatch.setattr(app_module, "_state_manager", StateManager(env_setup))

    client = UpsdClient("127.0.0.1", mock_upsd.port)
    await client.__aenter__()
    monkeypatch.setattr(app_module, "_upsd_client", client)

    from nut_up.app import create_app

    app = create_app()
    yield app

    await client.close()


@pytest.fixture
async def client(app_with_upsd):
    transport = ASGITransport(app=app_with_upsd)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_run_command(client):
    resp = await client.post(
        "/api/ups/myups/command",
        json={"command": "test.battery.start"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_set_variable(client):
    resp = await client.post(
        "/api/ups/myups/variable",
        json={"variable": "ups.delay.shutdown", "value": "30"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["variable"] == "ups.delay.shutdown"
    assert data["value"] == "30"
