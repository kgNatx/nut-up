"""Tests for the REST API endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def env_setup(tmp_path, monkeypatch):
    """Set environment variables for the app."""
    monkeypatch.setenv("NUT_UP_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("NUT_UP_UPSD_HOST", "127.0.0.1")
    monkeypatch.setenv("NUT_UP_UPSD_PORT", "0")


@pytest.fixture
def app(env_setup):
    from nut_up.app import create_app

    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def test_get_ups_list(client):
    resp = await client.get("/api/ups")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


async def test_get_server_info(client):
    resp = await client.get("/api/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert data["name"] == "nut-up"
