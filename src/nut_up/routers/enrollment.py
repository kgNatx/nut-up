"""Enrollment API endpoints."""

from __future__ import annotations

import socket

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from nut_up.enrollment import EnrollmentManager

router = APIRouter()


class CreateKeyRequest(BaseModel):
    label: str
    hours: int = 24


class EnrollConfirmRequest(BaseModel):
    key: str
    hostname: str
    ip: str


def _get_enrollment_manager() -> EnrollmentManager:
    from nut_up.app import get_state_manager

    return EnrollmentManager(get_state_manager())


def _get_local_ip() -> str:
    """Get the LAN IP address of this machine using the socket trick."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.post("/api/keys")
async def create_key(body: CreateKeyRequest) -> dict:
    em = _get_enrollment_manager()
    key = em.create_key(body.label, body.hours)
    return {"key": key}


@router.get("/api/keys")
async def list_keys() -> list:
    em = _get_enrollment_manager()
    return em.list_keys()


@router.delete("/api/keys/{key}")
async def delete_key(key: str) -> dict:
    em = _get_enrollment_manager()
    em.revoke_key(key)
    return {"status": "ok"}


@router.get("/api/clients")
async def list_clients() -> list:
    em = _get_enrollment_manager()
    return em.list_clients()


@router.get("/setup")
async def setup_endpoint(key: str, request: Request) -> PlainTextResponse:
    em = _get_enrollment_manager()
    if not em.validate_key(key):
        raise HTTPException(status_code=403, detail="Invalid or expired enrollment key")

    from nut_up.app import get_state_manager

    state = get_state_manager()
    data = state.load()
    server = data.get("server", {})

    ups_name = server.get("ups_name", "ups")
    monitor_password = server.get("monitor_password", "")

    # Determine server host from request headers or fall back to local IP
    server_host = request.headers.get("x-forwarded-host")
    if not server_host:
        host_header = request.headers.get("host", "")
        # Strip port from host header
        if ":" in host_header:
            server_host = host_header.rsplit(":", 1)[0]
        else:
            server_host = host_header
    if not server_host:
        server_host = _get_local_ip()

    # Determine the web UI port from the request
    web_port = request.url.port or 3494

    # Optional shutdown command override
    shutdown_cmd = request.query_params.get("shutdown_cmd", "/sbin/shutdown -h +0")

    script = em.generate_enrollment_script(
        key=key,
        server_host=server_host,
        server_port=3493,
        web_port=web_port,
        ups_name=ups_name,
        monitor_password=monitor_password,
        shutdown_cmd=shutdown_cmd,
    )
    return PlainTextResponse(script, media_type="text/x-shellscript")


@router.post("/api/enroll/confirm")
async def enrollment_confirm(body: EnrollConfirmRequest) -> dict:
    em = _get_enrollment_manager()
    if not em.validate_key(body.key):
        raise HTTPException(status_code=403, detail="Invalid or expired enrollment key")
    em.record_enrollment(body.key, body.hostname, body.ip)
    return {"status": "ok"}


@router.get("/unenroll")
async def unenroll_endpoint(request: Request) -> PlainTextResponse:
    """Serve a script that removes NUT client config from a machine."""
    server_host = request.headers.get("x-forwarded-host")
    if not server_host:
        host_header = request.headers.get("host", "")
        if ":" in host_header:
            server_host = host_header.rsplit(":", 1)[0]
        else:
            server_host = host_header
    if not server_host:
        server_host = _get_local_ip()

    web_port = request.url.port or 3494

    script = _generate_unenroll_script(server_host, web_port)
    return PlainTextResponse(script, media_type="text/x-shellscript")


def _generate_unenroll_script(server_host: str, web_port: int) -> str:
    return f"""#!/bin/bash
set -euo pipefail

echo "=== nut-up client removal ==="
echo ""

# Stop and disable nut-monitor
if systemctl is-active --quiet nut-monitor 2>/dev/null; then
    echo "Stopping nut-monitor..."
    systemctl stop nut-monitor
fi
if systemctl is-enabled --quiet nut-monitor 2>/dev/null; then
    systemctl disable nut-monitor
fi

# Remove NUT config files we created
if [ -f /etc/nut/nut.conf ]; then
    echo "Removing /etc/nut/nut.conf..."
    rm -f /etc/nut/nut.conf
fi
if [ -f /etc/nut/upsmon.conf ]; then
    echo "Removing /etc/nut/upsmon.conf..."
    rm -f /etc/nut/upsmon.conf
fi

# Remove nut-client package
echo "Removing nut-client package..."
if command -v apt-get &>/dev/null; then
    apt-get remove -y -qq nut-client
elif command -v dnf &>/dev/null; then
    dnf remove -y nut-client
elif command -v yum &>/dev/null; then
    yum remove -y nut-client
fi

# Proxmox: remove UPS info from node notes
if command -v pvesh &>/dev/null; then
    echo ""
    echo "Proxmox detected — cleaning node notes..."
    CURRENT=$(pvesh get /nodes/"$(hostname)"/config --output-format json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('description',''))" 2>/dev/null || echo "")
    if echo "$CURRENT" | grep -q "UPS Protected"; then
        CLEANED=$(echo "$CURRENT" | python3 -c "
import sys
text = sys.stdin.read()
# Remove the nut-up block (from ---\\nUPS Protected to next --- or end)
import re
text = re.sub(r'\\n?---\\n\\*\\*UPS Protected\\*\\*.*?(?=\\n---|$)', '', text, flags=re.DOTALL)
print(text.strip())
")
        pvesh set /nodes/"$(hostname)"/config --description "$CLEANED" 2>/dev/null \\
            && echo "  Node notes cleaned." \\
            || echo "  WARNING: Could not update node notes."
    fi
fi

# Notify server
HOSTNAME=$(hostname)
curl -s -X POST "http://{server_host}:{web_port}/api/enroll/remove" \\
    -H 'Content-Type: application/json' \\
    -d '{{"hostname": "'"$HOSTNAME"'"}}' 2>/dev/null || true

echo ""
echo "=== Client removed ==="
echo "This machine is no longer monitored by nut-up."
"""


@router.post("/api/enroll/remove")
async def enrollment_remove(body: dict) -> dict:
    """Remove a client from the enrolled list."""
    from nut_up.app import get_state_manager

    hostname = body.get("hostname", "")
    if not hostname:
        raise HTTPException(status_code=400, detail="hostname required")

    state = get_state_manager()

    def remove_client(data: dict) -> dict:
        data["clients"].pop(hostname, None)
        return data

    state.update(remove_client)
    return {"status": "ok", "hostname": hostname}


@router.get("/api/manual-setup")
async def manual_setup_info() -> dict:
    from nut_up.app import get_state_manager

    state = get_state_manager()
    data = state.load()
    server = data.get("server", {})

    return {
        "ups_name": server.get("ups_name", "ups"),
        "server_host": _get_local_ip(),
        "server_port": 3493,
        "monitor_user": "upsmon_secondary",
        "monitor_password": server.get("monitor_password", ""),
    }
