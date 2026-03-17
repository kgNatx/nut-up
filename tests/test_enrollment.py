"""Tests for enrollment key management and client enrollment logic."""

from __future__ import annotations

import pytest

from nut_up.enrollment import EnrollmentManager
from nut_up.state import StateManager


@pytest.fixture
def em(tmp_path):
    state = StateManager(tmp_path / "state.json")
    return EnrollmentManager(state)


def test_create_key(em):
    key = em.create_key("test-label")
    assert key.startswith("nutup_")
    keys = em.list_keys()
    assert len(keys) == 1
    assert keys[0]["label"] == "test-label"
    assert keys[0]["key"] == key
    assert not keys[0]["expired"]


def test_key_expires(em):
    key = em.create_key("expired-key", hours=-1)
    assert not em.validate_key(key)
    keys = em.list_keys()
    assert len(keys) == 1
    assert keys[0]["expired"]


def test_key_valid_before_expiry(em):
    key = em.create_key("valid-key", hours=24)
    assert em.validate_key(key)


def test_revoke_key(em):
    key = em.create_key("revoke-me")
    assert em.validate_key(key)
    em.revoke_key(key)
    assert not em.validate_key(key)
    assert len(em.list_keys()) == 0


def test_record_enrollment(em):
    em.record_enrollment("nutup_abc123", "myhost", "192.168.1.100")
    clients = em.list_clients()
    assert len(clients) == 1
    assert clients[0]["hostname"] == "myhost"
    assert clients[0]["ip"] == "192.168.1.100"
    assert clients[0]["key_used"] == "nutup_abc123"
    assert "enrolled_at" in clients[0]


def test_generate_enrollment_script(em):
    script = em.generate_enrollment_script(
        key="nutup_testkey",
        server_host="10.0.0.1",
        server_port=3493,
        web_port=3494,
        ups_name="myups",
        monitor_password="secret123",
    )
    assert "#!/bin/bash" in script
    assert "10.0.0.1" in script
    assert "myups" in script
    assert "secret123" in script
    assert "nutup_testkey" in script
    assert "upsmon_secondary" in script
    assert "MODE=netclient" in script
