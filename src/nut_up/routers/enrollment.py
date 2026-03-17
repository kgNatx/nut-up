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

    script = em.generate_enrollment_script(
        key=key,
        server_host=server_host,
        server_port=3493,
        ups_name=ups_name,
        monitor_password=monitor_password,
    )
    return PlainTextResponse(script, media_type="text/x-shellscript")


@router.post("/api/enroll/confirm")
async def enrollment_confirm(body: EnrollConfirmRequest) -> dict:
    em = _get_enrollment_manager()
    if not em.validate_key(body.key):
        raise HTTPException(status_code=403, detail="Invalid or expired enrollment key")
    em.record_enrollment(body.key, body.hostname, body.ip)
    return {"status": "ok"}


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
