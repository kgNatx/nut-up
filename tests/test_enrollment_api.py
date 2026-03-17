"""Tests for enrollment API endpoints."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

import nut_up.app as app_module
from nut_up.state import StateManager
from nut_up.ws import ConnectionManager


@pytest.fixture
def env_setup(tmp_path, monkeypatch):
    """Seed state.json with server config."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "keys": {},
        "clients": {},
        "server": {
            "mode": "netserver",
            "ups_name": "myups",
            "admin_password": "testpass",
            "monitor_password": "monpass",
        },
    }))
    monkeypatch.setenv("NUT_UP_STATE_FILE", str(state_file))
    monkeypatch.setenv("NUT_UP_UPSD_HOST", "127.0.0.1")
    monkeypatch.setenv("NUT_UP_UPSD_PORT", "0")
    return state_file


@pytest.fixture
def app(env_setup, monkeypatch):
    """Create the app with module-level singletons pre-configured."""
    monkeypatch.setattr(app_module, "_ws_manager", ConnectionManager())
    monkeypatch.setattr(app_module, "_state_manager", StateManager(env_setup))

    from nut_up.app import create_app

    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_create_and_list_keys(client):
    # Create a key
    resp = await client.post("/api/keys", json={"label": "test-key", "hours": 24})
    assert resp.status_code == 200
    data = resp.json()
    assert "key" in data
    key = data["key"]
    assert key.startswith("nutup_")

    # List keys
    resp = await client.get("/api/keys")
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) == 1
    assert keys[0]["label"] == "test-key"
    assert keys[0]["key"] == key


async def test_delete_key(client):
    # Create then delete
    resp = await client.post("/api/keys", json={"label": "to-delete"})
    key = resp.json()["key"]

    resp = await client.delete(f"/api/keys/{key}")
    assert resp.status_code == 200

    # Verify gone
    resp = await client.get("/api/keys")
    keys = resp.json()
    assert len(keys) == 0


async def test_setup_endpoint_invalid_key(client):
    resp = await client.get("/setup", params={"key": "invalid_key_123"})
    assert resp.status_code == 403


async def test_setup_endpoint_valid_key(client):
    # Create key first
    resp = await client.post("/api/keys", json={"label": "setup-key"})
    key = resp.json()["key"]

    resp = await client.get("/setup", params={"key": key})
    assert resp.status_code == 200
    body = resp.text
    assert "#!/bin/bash" in body
    assert "myups" in body


async def test_enrollment_confirm(client):
    # Create a key
    resp = await client.post("/api/keys", json={"label": "confirm-key"})
    key = resp.json()["key"]

    # Confirm enrollment
    resp = await client.post(
        "/api/enroll/confirm",
        json={"key": key, "hostname": "testhost", "ip": "10.0.0.50"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Check clients list
    resp = await client.get("/api/clients")
    assert resp.status_code == 200
    clients = resp.json()
    assert len(clients) >= 1
    assert any(c["hostname"] == "testhost" for c in clients)


async def test_manual_setup_info(client):
    resp = await client.get("/api/manual-setup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ups_name"] == "myups"
    assert data["server_port"] == 3493
    assert data["monitor_user"] == "upsmon_secondary"
    assert "monitor_password" in data
