"""Atomic JSON state manager."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

DEFAULTS: dict[str, Any] = {"keys": {}, "clients": {}, "server": {}}


class StateManager:
    """Manages persistent state as a JSON file with atomic writes."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        """Read state from disk. Creates the file with defaults if it doesn't exist."""
        if not self.path.exists():
            data = {**DEFAULTS}
            self.save(data)
            return data
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        """Atomically write state to disk (write to temp, then rename)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            Path(tmp).rename(self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def update(self, fn: Callable[[dict[str, Any]], Any]) -> Any:
        """Load state, apply fn(data), save, and return fn's result."""
        data = self.load()
        result = fn(data)
        self.save(data)
        return result
