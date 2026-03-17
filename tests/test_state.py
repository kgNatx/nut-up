"""Tests for the state manager."""

from pathlib import Path

from nut_up.state import StateManager


def test_fresh_state_has_defaults(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state.json")
    data = state.load()
    assert data == {"keys": {}, "clients": {}, "server": {}}
    assert (tmp_path / "state.json").exists()


def test_save_load_roundtrip(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state.json")
    original = {"keys": {"abc": "123"}, "clients": {"ups1": {}}, "server": {"port": 3493}}
    state.save(original)
    loaded = state.load()
    assert loaded == original


def test_atomic_write_produces_valid_json(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state.json")
    state.save({"keys": {}, "clients": {}, "server": {"host": "0.0.0.0"}})
    # Read the raw file content and verify it's valid JSON
    import json

    raw = (tmp_path / "state.json").read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed["server"]["host"] == "0.0.0.0"


def test_update_helper(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state.json")
    state.load()  # initialize

    def add_key(data: dict) -> str:
        data["keys"]["myups"] = "secret123"
        return "added"

    result = state.update(add_key)
    assert result == "added"

    # Verify it persisted
    data = state.load()
    assert data["keys"]["myups"] == "secret123"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested" / "state.json"
    state = StateManager(nested)
    state.save({"keys": {}, "clients": {}, "server": {}})
    assert nested.exists()


def test_multiple_updates(tmp_path: Path) -> None:
    state = StateManager(tmp_path / "state.json")

    state.update(lambda d: d["clients"].__setitem__("ups1", {"host": "10.0.0.1"}))
    state.update(lambda d: d["clients"].__setitem__("ups2", {"host": "10.0.0.2"}))

    data = state.load()
    assert "ups1" in data["clients"]
    assert "ups2" in data["clients"]
