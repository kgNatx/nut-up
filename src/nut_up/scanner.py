"""UPS scanner wrapping nut-scanner."""

from __future__ import annotations

import re
import subprocess
from typing import Any


def parse_nut_scanner_output(output: str) -> list[dict[str, Any]]:
    """Parse INI-style output from nut-scanner.

    Each section looks like:
        [nutdev1]
            driver = "usbhid-ups"
            port = "auto"
            product = "Back-UPS XS 1500M"
            vendorid = "051d"

    Returns a list of dicts with keys: name, driver, port, desc, extra.
    """
    devices: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    section_re = re.compile(r"^\[(.+)\]$")
    kv_re = re.compile(r'^\s*(\S+)\s*=\s*"(.*)"\s*$')

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        section_match = section_re.match(line)
        if section_match:
            if current is not None:
                devices.append(current)
            current = {
                "name": section_match.group(1),
                "driver": "",
                "port": "",
                "desc": "",
                "extra": {},
            }
            continue

        if current is None:
            continue

        # Skip malformed lines from nut-scanner (e.g. ###NOTMATCHED-YET###)
        if "###" in line:
            continue

        kv_match = kv_re.match(line)
        if kv_match:
            key, value = kv_match.group(1), kv_match.group(2)
            if key == "driver":
                current["driver"] = value
            elif key == "port":
                current["port"] = value
            elif key == "product":
                current["desc"] = value
            else:
                current["extra"][key] = value

    if current is not None:
        devices.append(current)

    return devices


def scan_usb() -> list[dict[str, Any]]:
    """Run nut-scanner -U and return parsed output.

    Returns an empty list if nut-scanner is not installed, times out,
    or exits with a non-zero status.
    """
    try:
        result = subprocess.run(
            ["nut-scanner", "-U"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return parse_nut_scanner_output(result.stdout)
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return []
