"""Enrollment key management and client enrollment logic."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from textwrap import dedent
from typing import Any

from nut_up.state import StateManager


class EnrollmentManager:
    """Manages enrollment keys and client registrations."""

    def __init__(self, state: StateManager) -> None:
        self.state = state

    def create_key(self, label: str, hours: int = 24) -> str:
        """Generate a new enrollment key with an expiration time."""
        key = "nutup_" + secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=hours)

        def _add(data: dict) -> None:
            data.setdefault("keys", {})[key] = {
                "label": label,
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
            }

        self.state.update(_add)
        return key

    def validate_key(self, key: str) -> bool:
        """Check if a key exists and has not expired."""
        data = self.state.load()
        keys = data.get("keys", {})
        if key not in keys:
            return False
        expires_at = datetime.fromisoformat(keys[key]["expires_at"])
        return datetime.now(timezone.utc) < expires_at

    def revoke_key(self, key: str) -> None:
        """Remove a key from state."""

        def _remove(data: dict) -> None:
            data.get("keys", {}).pop(key, None)

        self.state.update(_remove)

    def list_keys(self) -> list[dict[str, Any]]:
        """List all enrollment keys with their metadata."""
        data = self.state.load()
        keys = data.get("keys", {})
        now = datetime.now(timezone.utc)
        result = []
        for key, info in keys.items():
            expires_at = datetime.fromisoformat(info["expires_at"])
            result.append(
                {
                    "key": key,
                    "label": info["label"],
                    "created_at": info["created_at"],
                    "expires_at": info["expires_at"],
                    "expired": now >= expires_at,
                }
            )
        return result

    def record_enrollment(self, key: str, hostname: str, ip: str) -> None:
        """Record a client enrollment."""
        now = datetime.now(timezone.utc)

        def _record(data: dict) -> None:
            data.setdefault("clients", {})[hostname] = {
                "hostname": hostname,
                "ip": ip,
                "enrolled_at": now.isoformat(),
                "key_used": key,
            }

        self.state.update(_record)

    def list_clients(self) -> list[dict[str, Any]]:
        """List all enrolled clients."""
        data = self.state.load()
        clients = data.get("clients", {})
        return [
            {
                "hostname": info["hostname"],
                "ip": info["ip"],
                "enrolled_at": info["enrolled_at"],
                "key_used": info["key_used"],
            }
            for info in clients.values()
        ]

    def generate_enrollment_script(
        self,
        key: str,
        server_host: str,
        server_port: int,
        web_port: int,
        ups_name: str,
        monitor_password: str,
        shutdown_cmd: str = "/sbin/shutdown -h +0",
    ) -> str:
        """Generate a bash enrollment script for a client machine."""
        return dedent(f"""\
            #!/bin/bash
            set -euo pipefail

            echo "=== nut-up client enrollment ==="
            echo "Server: {server_host}:{server_port}"
            echo "UPS: {ups_name}"
            echo ""

            # Install nut-client
            if command -v apt-get &>/dev/null; then
                apt-get update -qq && apt-get install -y -qq nut-client
            elif command -v dnf &>/dev/null; then
                dnf install -y nut-client
            elif command -v yum &>/dev/null; then
                yum install -y nut-client
            else
                echo "ERROR: Could not detect package manager."
                exit 1
            fi

            # Write NUT config
            cat > /etc/nut/nut.conf << 'NUTEOF'
            MODE=netclient
            NUTEOF

            cat > /etc/nut/upsmon.conf << 'UPSMONEOF'
            MONITOR {ups_name}@{server_host}:{server_port} 1 upsmon_secondary {monitor_password} secondary
            SHUTDOWNCMD "{shutdown_cmd}"
            UPSMONEOF

            # Start nut-monitor
            systemctl enable nut-monitor
            systemctl restart nut-monitor

            # Verify connectivity
            echo "Verifying UPS connection..."
            if upsc {ups_name}@{server_host}:{server_port} ups.status 2>/dev/null; then
                echo "SUCCESS: UPS connection verified."
            else
                echo "WARNING: Could not verify UPS connection. Check server firewall."
            fi

            # Phone home
            HOSTNAME=$(hostname)
            IP=$(hostname -I | awk '{{print $1}}')
            curl -s -X POST http://{server_host}:{web_port}/api/enroll/confirm \\
                -H 'Content-Type: application/json' \\
                -d '{{"key": "{key}", "hostname": "'"$HOSTNAME"'", "ip": "'"$IP"'"}}'

            echo ""
            echo "=== Enrollment complete ==="
        """)
