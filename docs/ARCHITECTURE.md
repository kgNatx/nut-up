# nut-up Architecture

## Overview

nut-up is a bare-metal wrapper around NUT (Network UPS Tools) that automates server setup, provides a modern web dashboard, and enables one-command client enrollment. It runs on a Raspberry Pi (or any Linux box) connected to a UPS via USB.

## System Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi (NUT Server + nut-up)                      │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌───────────────────┐  │
│  │ UPS      │USB │ NUT      │TCP │ nut-up            │  │
│  │ (CyberPower)──│ upsd     │:3493│ FastAPI           │  │
│  │          │    │ upsmon   │    │ :3494             │  │
│  │          │    │ drivers  │    │                   │  │
│  └──────────┘    └──────────┘    └───────────────────┘  │
│                                    │ WebSocket + REST    │
│                                    │ Static HTML/CSS/JS  │
└────────────────────────────────────│─────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
               ┌────▼────┐    ┌─────▼─────┐    ┌────▼────┐
               │ Browser │    │ Proxmox   │    │ OPNsense│
               │ Dashboard│    │ (enrolled)│    │ (manual)│
               └─────────┘    └───────────┘    └─────────┘
```

## Components

### 1. CLI (`cli.py`)

Entry point: `nut-up` command with subcommands.

- `nut-up server` — Setup wizard: installs NUT, scans USB for UPS via `nut-scanner`, generates all 5 NUT config files, fixes USB permissions (udev trigger + verify), starts NUT services + web UI systemd service, prints dashboard URL and next steps.
- `nut-up start/stop/status` — Manages both NUT services and nut-up web UI service.
- `nut-up web` — Runs web UI in foreground (dev mode) with configurable host/port/upsd connection.

### 2. NUT Protocol Client (`upsd_client.py`)

Async TCP client that speaks the NUT text protocol to upsd on port 3493.

- Line-oriented text protocol over TCP
- Commands: `LIST UPS`, `LIST VAR`, `LIST RW`, `LIST CMD`, `LIST CLIENT`, `GET VAR`, `SET VAR`, `INSTCMD`, `USERNAME`/`PASSWORD` auth
- Responses: `BEGIN LIST`/`END LIST` blocks, `VAR ups name "value"` lines, `ERR CODE` errors
- Double-quoted values with backslash escaping
- Supports context manager (`async with UpsdClient() as client:`)
- Public `connect()` method for reconnection

### 3. FastAPI Web Server (`app.py`)

App factory pattern with lifespan context manager.

**Module-level singletons** (set during lifespan):
- `_ws_manager` — WebSocket connection manager
- `_upsd_client` — shared upsd connection for polling
- `_state_manager` — JSON state file access
- `_latest_ups_data` — cached latest poll result
- `_ups_history` — `collections.deque(maxlen=900)` per UPS, 30 min of metrics

**Background polling loop** (`_poll_ups`):
- Every 2 seconds: poll all UPS devices via upsd, build data dict, append to history deque, broadcast to WebSocket clients
- On error: log, broadcast error, close connection, sleep 5s, reconnect via `client.connect()`

**Routers:**
- `routers/api.py` — REST: `/api/info`, `/api/ups`, `/api/ups/{name}`, `/api/ups/{name}/variables`, `/api/ups/{name}/rw`, `/api/ups/{name}/commands`, `/api/ups/{name}/clients`, `/api/ups/{name}/history`, `/api/descriptions`
- `routers/commands.py` — Write ops: `POST /api/ups/{name}/command`, `POST /api/ups/{name}/variable`. Creates a separate authenticated upsd connection per request (doesn't reuse polling connection).
- `routers/enrollment.py` — Enrollment: `POST /api/keys`, `GET /api/keys`, `DELETE /api/keys/{key}`, `GET /api/clients`, `GET /setup?key=...`, `POST /api/enroll/confirm`, `POST /api/enroll/remove`, `GET /unenroll`, `GET /api/manual-setup`
- `routers/ws.py` — WebSocket: `/ws`

**Static files** mounted at `/` last (after all API routes) with `html=True` for SPA.

### 4. State Management (`state.py`)

Simple JSON file at `/var/lib/nut-up/state.json` (configurable via env).

```json
{
  "keys": { "nutup_abc123": { "label": "...", "created_at": "...", "expires_at": "..." } },
  "clients": { "hostname": { "ip": "...", "enrolled_at": "...", "key_used": "..." } },
  "server": { "ups_name": "...", "admin_password": "...", "monitor_password": "...", ... }
}
```

- Atomic writes: write to temp file, then rename
- `update(fn)` pattern for read-modify-write

### 5. Config Generation (`config.py`)

Generates all 5 NUT config files to `/etc/nut/`:

| File | Content |
|------|---------|
| `nut.conf` | `MODE=netserver` (always netserver for client support) |
| `ups.conf` | UPS section with driver, port, vendorid, productid (scanner metadata filtered out) |
| `upsd.conf` | `LISTEN 0.0.0.0 3493`, `MAXAGE 15` |
| `upsd.users` | admin (SET/FSD/ALL), upsmon_primary, upsmon_secondary |
| `upsmon.conf` | MONITOR line, SHUTDOWNCMD, POLLFREQ, NOTIFYMSG/FLAG |

Backs up existing configs to `.bak.{timestamp}` before overwriting.

**Scanner metadata filtering**: `bus`, `device`, `busport`, `bcdDevice`, `product`, `vendor`, `serial`, and `###NOTMATCHED-YET###` lines are stripped from ups.conf — they crash the NUT driver.

### 6. Client Enrollment (`enrollment.py`)

**Key-based enrollment:**
- Admin creates time-limited reusable keys from web UI (10min to 7 days)
- Keys are `nutup_` + `secrets.token_urlsafe(16)`
- `GET /setup?key=...` returns a bash script that:
  1. Installs `nut-client` package
  2. Writes `nut.conf` (MODE=netclient) and `upsmon.conf` (MONITOR line)
  3. Resets failed state + starts `nut-monitor`
  4. Verifies UPS connectivity via `upsc`
  5. Phones home to `POST /api/enroll/confirm` on port 3494
  6. On Proxmox: appends UPS info to node notes via `pvesh`
- Optional `shutdown_cmd` query param for custom shutdown scripts

**Unenrollment:**
- `GET /unenroll` returns a bash script that stops services, removes configs, removes nut-client package, cleans Proxmox node notes, notifies server

### 7. Web UI (`static/`)

Single-page app with hash-based routing. Vanilla HTML/CSS/JS, no build step, no dependencies.

**Pages:**
- **Dashboard** — Real-time UPS monitoring with ring gauges (battery %, load watts, runtime), voltage sparkline charts (canvas), load history area chart, health indicator (green/yellow/red card border), bottom info bar
- **Enrollment** — Create keys with label/expiry/shutdown-cmd, active keys table with Copy URL + Revoke, enrolled clients table with Remove, unenroll command
- **Commands** — Instant commands table with descriptions and Run buttons (dangerous commands red on hover with warning confirm), writable variables table with descriptions and Set buttons
- **Variables** — All NUT variables grouped by prefix, descriptions, inline editing for writable vars (RW badge), copy buttons for read-only
- **Manual Setup** — Connection details with copy buttons for appliances (OPNsense, Synology, TrueNAS), upsmon.conf MONITOR line

**Key patterns:**
- `App.escapeHtml()` / `App.escapeAttr()` for all dynamic values (XSS prevention)
- `App._history` — client-side ring buffer, pre-loaded from `/api/ups/{name}/history` on page load
- WebSocket refreshes only the dashboard; other pages are static until navigated
- Input focus preserved across dashboard refreshes (save/restore id, value, cursor position)
- `App._descriptions` cached from `/api/descriptions` for variable/command explanations

### 8. Descriptions (`descriptions.py`)

Built-in human-readable descriptions for ~60 NUT variables and ~25 instant commands. Served via `/api/descriptions`. Fallback for NUT's often-empty `GET DESC` responses.

### 9. Service Management (`services.py`)

Thin wrappers around `systemctl` for:
- NUT units: `nut-driver-enumerator`, `nut-server`, `nut-monitor`
- nut-up unit: `nut-up` (web UI)
- NUT installation: `which upsd`, `apt-get install nut`

### 10. Packaging

- **systemd unit** (`scripts/nut-up.service`): runs `nut-up web --host 0.0.0.0 --port 3494`, restarts on failure
- **Install script** (`scripts/nut-up-install.sh`): downloads GitHub tarball (no git required), creates venv, pip installs, symlinks CLI, installs systemd unit, opens UFW ports 3494+3493
- **Remove script** (`scripts/nut-up-remove.sh`): stops services, removes systemd unit, CLI symlink, `/opt/nut-up/`, closes UFW port 3494

## Data Flow

### Real-time Dashboard
```
UPS ──USB──▶ NUT driver ──▶ upsd ──TCP:3493──▶ nut-up _poll_ups (2s loop)
                                                    │
                                                    ├──▶ _latest_ups_data (cache)
                                                    ├──▶ _ups_history (deque, 30min)
                                                    └──▶ WebSocket broadcast
                                                              │
                                                    Browser ◀─┘ (updates dashboard)
```

### Client Enrollment
```
Admin creates key in web UI
    │
    ▼
POST /api/keys ──▶ state.json (stores key + expiry)
    │
    ▼
Admin copies curl command, runs on client machine
    │
    ▼
GET /setup?key=... ──▶ returns bash script
    │
    ▼
Client runs script ──▶ installs nut-client, writes configs, starts upsmon
    │
    ▼
Script phones home ──▶ POST /api/enroll/confirm ──▶ state.json (records client)
    │
    ▼
(If Proxmox) ──▶ pvesh updates node notes
```

## File Layout

```
/opt/nut-up/                    # Install directory
├── venv/                       # Python virtual environment
├── src/nut_up/                 # Python package
│   ├── __init__.py             # Version
│   ├── cli.py                  # CLI entry point
│   ├── app.py                  # FastAPI factory + polling
│   ├── upsd_client.py          # NUT protocol client
│   ├── config.py               # NUT config generation
│   ├── scanner.py              # nut-scanner wrapper
│   ├── state.py                # JSON state management
│   ├── enrollment.py           # Key + enrollment logic
│   ├── services.py             # systemd helpers
│   ├── descriptions.py         # Variable/command descriptions
│   ├── ws.py                   # WebSocket manager
│   ├── routers/                # FastAPI route modules
│   └── static/                 # Web UI (HTML/CSS/JS)
├── tests/                      # 58 tests
└── scripts/                    # Install/remove/systemd

/etc/nut/                       # NUT config (generated by nut-up)
/var/lib/nut-up/state.json      # nut-up state (keys, clients, server config)
/etc/systemd/system/nut-up.service  # systemd unit
/usr/local/bin/nut-up           # CLI symlink
```

## Key Design Decisions

- **No Docker** — UPS safety system shouldn't have container failure modes (USB passthrough, can't shut down host)
- **No database** — JSON state file + in-memory deque. Simple, no deps, adequate for the scale
- **No frontend build step** — vanilla JS, served as static files. Works on a Pi, no Node.js needed
- **Always netserver mode** — even for single-machine setups, because clients may enroll later
- **Separate auth connection for writes** — polling connection stays read-only, command/variable writes create a new authenticated connection per request
- **Server-side history in memory** — 30 min in deque (~45KB/UPS), charts populate instantly on page load, vanishes on restart (acceptable)
- **Scanner metadata filtering** — nut-scanner outputs USB bus/device info and `###NOTMATCHED-YET###` lines that crash the NUT driver if written to ups.conf
- **udev trigger in setup wizard** — NUT's udev rules may not fire on package install; explicitly trigger + verify + fallback chmod

## Target Environment

- **Server**: Raspberry Pi (Debian/Pi OS) with USB UPS
- **Clients**: Proxmox hosts (Debian), any Linux with apt/dnf/yum
- **Appliances**: OPNsense, Synology, TrueNAS (manual setup via web UI)
- **Network**: LAN only, HTTP (not HTTPS). Clipboard fallback for HTTP contexts.
