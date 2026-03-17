"""Shared fixtures and MockUpsd server for testing."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nut_up.state import StateManager


# ---------------------------------------------------------------------------
# MockUpsd — minimal NUT upsd protocol simulator
# ---------------------------------------------------------------------------

SAMPLE_UPS = "myups"
SAMPLE_DESC = "Test UPS (mock)"

SAMPLE_VARS: dict[str, str] = {
    "ups.status": "OL",
    "ups.load": "25",
    "ups.model": "Mock UPS 1000",
    "ups.mfr": "MockCorp",
    "battery.charge": "100",
    "battery.runtime": "3600",
    "battery.voltage": "13.4",
    "input.voltage": "120.0",
    "input.frequency": "60.0",
    "output.voltage": "120.0",
    "output.frequency": "60.0",
}

SAMPLE_RW: dict[str, str] = {
    "ups.delay.shutdown": "20",
    "ups.delay.start": "30",
}

SAMPLE_CMDS: list[str] = [
    "test.battery.start",
    "test.battery.stop",
    "shutdown.return",
    "beeper.toggle",
]


class MockUpsd:
    """A minimal async TCP server that simulates the NUT upsd protocol."""

    def __init__(self) -> None:
        self.host = "127.0.0.1"
        self.port: int = 0  # assigned on start
        self._server: asyncio.Server | None = None
        self._authenticated: dict[int, bool] = {}  # fd -> authenticated
        self._valid_user = "admin"
        self._valid_pass = "testpass"

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, 0)
        addr = self._server.sockets[0].getsockname()
        self.port = addr[1]

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        client_id = id(writer)
        self._authenticated[client_id] = False
        username_set = False

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                line = data.decode().rstrip("\n").rstrip("\r")
                if not line:
                    continue

                response = self._process_command(line, client_id, username_set)
                if isinstance(response, list):
                    for r in response:
                        writer.write(f"{r}\n".encode())
                else:
                    writer.write(f"{response}\n".encode())
                await writer.drain()

                # Track USERNAME state for multi-step auth
                if line.startswith("USERNAME "):
                    parts = line.split(" ", 1)
                    if len(parts) == 2 and parts[1] == self._valid_user:
                        username_set = True

                if line == "LOGOUT":
                    break
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            self._authenticated.pop(client_id, None)
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    def _process_command(
        self, line: str, client_id: int, username_set: bool
    ) -> str | list[str]:
        cmd_parts = line.split()
        cmd = cmd_parts[0] if cmd_parts else ""

        if cmd == "VER":
            return "Network UPS Tools upsd 2.8.0 - mock"

        if cmd == "LOGOUT":
            return "OK Goodbye"

        if cmd == "LIST":
            return self._handle_list(cmd_parts)

        if cmd == "GET":
            return self._handle_get(cmd_parts)

        if cmd == "USERNAME":
            if len(cmd_parts) < 2:
                return "ERR INVALID-ARGUMENT"
            if cmd_parts[1] == self._valid_user:
                return "OK"
            return "ERR ACCESS-DENIED"

        if cmd == "PASSWORD":
            if len(cmd_parts) < 2:
                return "ERR INVALID-ARGUMENT"
            if username_set and cmd_parts[1] == self._valid_pass:
                self._authenticated[client_id] = True
                return "OK"
            return "ERR ACCESS-DENIED"

        if cmd == "SET":
            return self._handle_set(cmd_parts, client_id)

        if cmd == "INSTCMD":
            return self._handle_instcmd(cmd_parts, client_id)

        return "ERR UNKNOWN-COMMAND"

    def _handle_list(self, parts: list[str]) -> str | list[str]:
        if len(parts) < 2:
            return "ERR INVALID-ARGUMENT"

        list_type = parts[1]

        if list_type == "UPS":
            return [
                "BEGIN LIST UPS",
                f'UPS {SAMPLE_UPS} "{SAMPLE_DESC}"',
                "END LIST UPS",
            ]

        # All remaining LIST types need a UPS name
        if len(parts) < 3:
            return "ERR INVALID-ARGUMENT"

        ups_name = parts[2]
        if ups_name != SAMPLE_UPS:
            return "ERR UNKNOWN-UPS"

        if list_type == "VAR":
            lines = [f"BEGIN LIST VAR {ups_name}"]
            for var, val in SAMPLE_VARS.items():
                lines.append(f'VAR {ups_name} {var} "{val}"')
            lines.append(f"END LIST VAR {ups_name}")
            return lines

        if list_type == "RW":
            lines = [f"BEGIN LIST RW {ups_name}"]
            for var, val in SAMPLE_RW.items():
                lines.append(f'RW {ups_name} {var} "{val}"')
            lines.append(f"END LIST RW {ups_name}")
            return lines

        if list_type == "CMD":
            lines = [f"BEGIN LIST CMD {ups_name}"]
            for cmd in SAMPLE_CMDS:
                lines.append(f"CMD {ups_name} {cmd}")
            lines.append(f"END LIST CMD {ups_name}")
            return lines

        if list_type == "CLIENT":
            lines = [
                f"BEGIN LIST CLIENT {ups_name}",
                f"CLIENT {ups_name} 127.0.0.1",
                f"END LIST CLIENT {ups_name}",
            ]
            return lines

        return "ERR INVALID-ARGUMENT"

    def _handle_get(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return "ERR INVALID-ARGUMENT"

        get_type = parts[1]

        if get_type == "VAR":
            if len(parts) < 4:
                return "ERR INVALID-ARGUMENT"
            ups_name = parts[2]
            var_name = parts[3]
            if ups_name != SAMPLE_UPS:
                return "ERR UNKNOWN-UPS"
            all_vars = {**SAMPLE_VARS, **SAMPLE_RW}
            if var_name not in all_vars:
                return "ERR VAR-NOT-SUPPORTED"
            return f'VAR {ups_name} {var_name} "{all_vars[var_name]}"'

        if get_type == "UPSDESC":
            ups_name = parts[2]
            if ups_name != SAMPLE_UPS:
                return "ERR UNKNOWN-UPS"
            return f'UPSDESC {ups_name} "{SAMPLE_DESC}"'

        if get_type == "NUMLOGINS":
            ups_name = parts[2]
            if ups_name != SAMPLE_UPS:
                return "ERR UNKNOWN-UPS"
            return f"NUMLOGINS {ups_name} 1"

        return "ERR INVALID-ARGUMENT"

    def _handle_set(self, parts: list[str], client_id: int) -> str:
        # SET VAR ups varname "value"
        if not self._authenticated.get(client_id, False):
            return "ERR ACCESS-DENIED"
        if len(parts) < 5:
            return "ERR INVALID-ARGUMENT"
        ups_name = parts[2]
        if ups_name != SAMPLE_UPS:
            return "ERR UNKNOWN-UPS"
        return "OK"

    def _handle_instcmd(self, parts: list[str], client_id: int) -> str:
        # INSTCMD ups cmdname
        if not self._authenticated.get(client_id, False):
            return "ERR ACCESS-DENIED"
        if len(parts) < 3:
            return "ERR INVALID-ARGUMENT"
        ups_name = parts[1]
        if ups_name != SAMPLE_UPS:
            return "ERR UNKNOWN-UPS"
        cmd_name = parts[2]
        if cmd_name not in SAMPLE_CMDS:
            return "ERR CMD-NOT-SUPPORTED"
        return "OK"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_upsd():
    """Start a MockUpsd server and yield it; stop on teardown."""
    server = MockUpsd()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


@pytest.fixture
def state(state_file: Path) -> StateManager:
    return StateManager(state_file)
