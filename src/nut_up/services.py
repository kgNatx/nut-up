"""Systemd service management helpers for NUT and nut-up."""

from __future__ import annotations

import shutil
import subprocess

# NUT systemd units in startup order
NUT_UNITS = ["nut-driver-enumerator", "nut-server", "nut-monitor"]

# nut-up web service unit
NUT_UP_WEB_UNIT = "nut-up"


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


# ---------------------------------------------------------------------------
# NUT server services
# ---------------------------------------------------------------------------


def start_nut_server() -> None:
    """Enable and start all NUT server units."""
    for unit in NUT_UNITS:
        _run(["systemctl", "enable", "--now", unit], check=True)


def stop_nut_server() -> None:
    """Stop all NUT server units (reverse order)."""
    for unit in reversed(NUT_UNITS):
        _run(["systemctl", "stop", unit])


def restart_nut_server() -> None:
    """Restart all NUT server units."""
    stop_nut_server()
    start_nut_server()


def nut_server_status() -> dict[str, str]:
    """Return {unit: is-active output} for each NUT unit."""
    status: dict[str, str] = {}
    for unit in NUT_UNITS:
        result = _run(["systemctl", "is-active", unit])
        status[unit] = result.stdout.strip()
    return status


# ---------------------------------------------------------------------------
# nut-up web service
# ---------------------------------------------------------------------------


def start_nut_up_web() -> None:
    """Enable and start the nut-up web service."""
    _run(["systemctl", "enable", "--now", NUT_UP_WEB_UNIT], check=True)


def stop_nut_up_web() -> None:
    """Stop the nut-up web service."""
    _run(["systemctl", "stop", NUT_UP_WEB_UNIT])


def nut_up_web_status() -> str:
    """Return is-active output for the nut-up web service."""
    result = _run(["systemctl", "is-active", NUT_UP_WEB_UNIT])
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# NUT installation helpers
# ---------------------------------------------------------------------------


def is_nut_installed() -> bool:
    """Check if NUT is installed by looking for upsd."""
    return shutil.which("upsd") is not None


def install_nut_packages() -> None:
    """Install the nut package via apt-get."""
    _run(["apt-get", "install", "-y", "nut"], check=True)
