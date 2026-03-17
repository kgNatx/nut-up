# nut-up

A modern wrapper around [NUT (Network UPS Tools)](https://networkupstools.org/) that makes setup painless and monitoring beautiful. No forks, no patches — wraps existing NUT and handles everything it makes you do manually.

## What it does

- **Setup wizard** — auto-detects your USB UPS, generates all 5 NUT config files, starts services
- **Web dashboard** — real-time battery/load gauges, voltage readings, temperature, variable browser, instant commands
- **Client enrollment** — create a time-limited key, run one curl command on each client machine, done
- **Manual setup view** — connection details with copy buttons for appliances (OPNsense, Synology, TrueNAS)

## Install

```bash
curl -sL https://raw.githubusercontent.com/kgNatx/nut-up/main/scripts/nut-up-install.sh | sudo bash
```

This downloads nut-up to `/opt/nut-up/`, creates a Python venv, installs the CLI, and sets up the systemd service. No git required. If UFW is active, it opens ports 3494 (web UI) and 3493 (NUT upsd).

## Setup

```bash
sudo nut-up server
```

The wizard will:
1. Install NUT if needed
2. Scan for USB UPS devices
3. Generate NUT configs with secure random passwords
4. Start NUT services + web UI

Then open `http://<your-ip>:3494` in your browser.

## Enroll clients

From the web UI, go to **Enrollment** and create a key. Then on each client machine:

```bash
curl -sL "http://<server-ip>:3494/setup?key=nutup_abc123..." | sudo bash
```

This installs `nut-client`, configures `upsmon`, and starts monitoring. The machine will shut down safely when the UPS battery is low.

For appliances with their own NUT client (OPNsense, Synology, TrueNAS), use the **Manual Setup** page — it shows connection details with copy buttons.

## CLI

```
nut-up server    # Run setup wizard
nut-up start     # Start NUT + web UI services
nut-up stop      # Stop everything
nut-up status    # Show service status
nut-up web       # Run web UI in foreground (dev mode)
```

## Uninstall

```bash
curl -sL https://raw.githubusercontent.com/kgNatx/nut-up/main/scripts/nut-up-remove.sh | sudo bash
```

Stops services, removes nut-up. Leaves NUT and its config files in place.

## Development

```bash
git clone https://github.com/kgNatx/nut-up.git
cd nut-up
make dev     # pip install -e ".[dev]"
make test    # pytest
make run     # start web UI on :3494 (needs upsd running)
```

## Requirements

- Linux (Debian/Ubuntu/Raspberry Pi OS)
- Python 3.11+
- USB-connected UPS
- NUT (installed automatically by the setup wizard)
