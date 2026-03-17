# nut-up

A modern wrapper around NUT (Network UPS Tools) — painless setup, beautiful monitoring.

## Tech Stack

- **Python 3.11+** with type hints throughout
- **FastAPI** for the web API and dashboard
- **asyncio** TCP client for NUT upsd protocol communication
- **Hatchling** build backend

## Project Layout

```
src/nut_up/
  __init__.py        # Package root, version
  __main__.py        # python -m nut_up support
  cli.py             # CLI entry point
  state.py           # Atomic JSON state manager
  upsd_client.py     # Async NUT upsd protocol client
tests/
  conftest.py        # Shared fixtures, MockUpsd server
  test_state.py
  test_upsd_client.py
```

## Dev Setup

```bash
make dev          # Create venv + install editable with dev deps
make test         # Run pytest -v
make lint         # Run ruff check
make format       # Run ruff format
```

Or manually:

```bash
pip install -e ".[dev]"
pytest -v
```

## Key Patterns

- **State**: All persistent config lives in a single JSON file managed by `StateManager` with atomic writes (write-to-temp + rename).
- **upsd client**: Async context manager (`async with UpsdClient(...) as c:`). All methods are async. Raises `NUTError` on protocol errors.
- **NUT protocol**: Line-based TCP. LIST commands return BEGIN/END delimited blocks. Values are double-quoted, backslash-escaped.

## Testing

- `pytest` with `anyio` for async tests (`@pytest.mark.anyio`)
- `MockUpsd` in conftest.py simulates the NUT upsd daemon on a random port
- All tests use `tmp_path` for state files — no filesystem pollution

## NUT Config Files Reference

- `/etc/nut/nut.conf` — mode (standalone, netserver, netclient, none)
- `/etc/nut/ups.conf` — UPS device definitions (driver, port, desc)
- `/etc/nut/upsd.conf` — upsd daemon config (LISTEN directives, max connections)
- `/etc/nut/upsd.users` — upsd user accounts (password, actions, instcmds, upsmon role)
- `/etc/nut/upsmon.conf` — monitoring config (MONITOR lines, SHUTDOWNCMD)
