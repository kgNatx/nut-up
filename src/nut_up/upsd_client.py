"""Async client for the NUT upsd protocol."""

from __future__ import annotations

import asyncio
import re
from typing import Self


class NUTError(Exception):
    """Error returned by the NUT upsd daemon."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"ERR {code}" + (f" {detail}" if detail else ""))


# Regex to extract a double-quoted value, handling backslash escapes
_QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _parse_quoted(s: str) -> str:
    """Extract the first double-quoted value from a string."""
    m = _QUOTED_RE.search(s)
    if m is None:
        return s
    return m.group(1).replace("\\\\", "\\").replace('\\"', '"')


class UpsdClient:
    """Async TCP client for the NUT upsd protocol.

    Usage::

        async with UpsdClient("localhost", 3493) as client:
            ups_list = await client.list_ups()
    """

    def __init__(self, host: str = "localhost", port: int = 3493) -> None:
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Open the TCP connection to upsd."""
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the connection."""
        if self._writer is not None:
            try:
                self._writer.write(b"LOGOUT\n")
                await self._writer.drain()
            except (ConnectionError, OSError):
                pass
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            self._writer = None
            self._reader = None

    async def _send(self, command: str) -> str:
        """Send a command and return the response line."""
        assert self._writer is not None and self._reader is not None
        self._writer.write(f"{command}\n".encode())
        await self._writer.drain()
        line = await self._reader.readline()
        response = line.decode().rstrip("\n")
        self._check_error(response)
        return response

    async def _send_list(self, command: str) -> list[str]:
        """Send a LIST command and return all lines between BEGIN/END markers."""
        assert self._writer is not None and self._reader is not None
        self._writer.write(f"{command}\n".encode())
        await self._writer.drain()

        # Read the BEGIN line
        begin_line = (await self._reader.readline()).decode().rstrip("\n")
        self._check_error(begin_line)
        if not begin_line.startswith("BEGIN "):
            raise NUTError("PROTOCOL", f"Expected BEGIN, got: {begin_line}")

        lines: list[str] = []
        while True:
            line = (await self._reader.readline()).decode().rstrip("\n")
            if line.startswith("END "):
                break
            lines.append(line)

        return lines

    @staticmethod
    def _check_error(response: str) -> None:
        """Raise NUTError if the response is an error."""
        if response.startswith("ERR "):
            parts = response[4:].split(" ", 1)
            code = parts[0]
            detail = parts[1] if len(parts) > 1 else ""
            raise NUTError(code, detail)

    # --- Query methods ---

    async def server_version(self) -> str:
        """Get the server version string."""
        return await self._send("VER")

    async def list_ups(self) -> dict[str, str]:
        """List available UPS devices. Returns {name: description}."""
        lines = await self._send_list("LIST UPS")
        result: dict[str, str] = {}
        for line in lines:
            # UPS name "description"
            if line.startswith("UPS "):
                parts = line[4:].split(" ", 1)
                name = parts[0]
                desc = _parse_quoted(parts[1]) if len(parts) > 1 else ""
                result[name] = desc
        return result

    async def list_vars(self, ups: str) -> dict[str, str]:
        """List all variables for a UPS. Returns {var_name: value}."""
        lines = await self._send_list(f"LIST VAR {ups}")
        result: dict[str, str] = {}
        for line in lines:
            # VAR ups varname "value"
            if line.startswith("VAR "):
                rest = line[4:]
                parts = rest.split(" ", 2)
                if len(parts) >= 3:
                    var_name = parts[1]
                    result[var_name] = _parse_quoted(parts[2])
        return result

    async def list_rw(self, ups: str) -> dict[str, str]:
        """List read/write variables for a UPS. Returns {var_name: value}."""
        lines = await self._send_list(f"LIST RW {ups}")
        result: dict[str, str] = {}
        for line in lines:
            # RW ups varname "value"
            if line.startswith("RW "):
                rest = line[3:]
                parts = rest.split(" ", 2)
                if len(parts) >= 3:
                    var_name = parts[1]
                    result[var_name] = _parse_quoted(parts[2])
        return result

    async def list_commands(self, ups: str) -> list[str]:
        """List available instant commands for a UPS."""
        lines = await self._send_list(f"LIST CMD {ups}")
        result: list[str] = []
        for line in lines:
            # CMD ups cmdname
            if line.startswith("CMD "):
                parts = line[4:].split(" ", 1)
                if len(parts) >= 2:
                    result.append(parts[1])
        return result

    async def list_clients(self, ups: str) -> list[str]:
        """List clients connected to a UPS."""
        lines = await self._send_list(f"LIST CLIENT {ups}")
        result: list[str] = []
        for line in lines:
            # CLIENT ups ipaddr
            if line.startswith("CLIENT "):
                parts = line[7:].split(" ", 1)
                if len(parts) >= 2:
                    result.append(parts[1])
        return result

    async def get_var(self, ups: str, var: str) -> str:
        """Get a single variable value."""
        response = await self._send(f"GET VAR {ups} {var}")
        # VAR ups varname "value"
        return _parse_quoted(response)

    async def get_ups_desc(self, ups: str) -> str:
        """Get the description of a UPS."""
        response = await self._send(f"GET UPSDESC {ups}")
        return _parse_quoted(response)

    async def get_num_logins(self, ups: str) -> int:
        """Get the number of logged-in clients for a UPS."""
        response = await self._send(f"GET NUMLOGINS {ups}")
        # NUMLOGINS ups count
        parts = response.split()
        return int(parts[-1])

    # --- Auth + mutation methods ---

    async def authenticate(self, username: str, password: str) -> None:
        """Authenticate with the upsd server."""
        await self._send(f"USERNAME {username}")
        await self._send(f"PASSWORD {password}")

    async def set_var(self, ups: str, var: str, value: str) -> None:
        """Set a variable on a UPS (requires authentication)."""
        await self._send(f'SET VAR {ups} {var} "{value}"')

    async def run_command(self, ups: str, cmd: str) -> None:
        """Run an instant command on a UPS (requires authentication)."""
        await self._send(f"INSTCMD {ups} {cmd}")
