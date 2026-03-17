"""CLI entry point for nut-up."""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

from nut_up import __version__
from nut_up.config import NUTConfigReader, NUTConfigWriter
from nut_up.scanner import scan_usb
from nut_up.services import (
    install_nut_packages,
    is_nut_installed,
    nut_server_status,
    start_nut_server,
    stop_nut_server,
)
from nut_up.state import StateManager

DEFAULT_STATE_FILE = Path("/var/lib/nut-up/state.json")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="nut-up",
        description="A modern wrapper around NUT -- painless setup, beautiful monitoring.",
    )
    parser.add_argument("--version", action="version", version=f"nut-up {__version__}")

    sub = parser.add_subparsers(dest="command")

    # --- server ---
    server_p = sub.add_parser("server", help="Run the server setup wizard")
    server_p.add_argument(
        "--conf-dir", default="/etc/nut", help="NUT config directory (default: /etc/nut)"
    )
    server_p.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Path to nut-up state file",
    )
    server_p.add_argument(
        "--ups-name", default=None, help="Override the UPS name (default: auto-detect)"
    )
    server_p.add_argument(
        "--no-start",
        action="store_true",
        help="Don't start NUT services after configuration",
    )

    # --- start ---
    sub.add_parser("start", help="Start all NUT services")

    # --- stop ---
    sub.add_parser("stop", help="Stop all NUT services")

    # --- status ---
    sub.add_parser("status", help="Show NUT service status")

    # --- web ---
    web_p = sub.add_parser("web", help="Run the web UI in foreground (dev mode)")
    web_p.add_argument("--host", default="0.0.0.0", help="Listen host (default: 0.0.0.0)")
    web_p.add_argument("--port", type=int, default=3494, help="Listen port (default: 3494)")
    web_p.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Path to nut-up state file",
    )
    web_p.add_argument("--upsd-host", default="localhost", help="upsd host (default: localhost)")
    web_p.add_argument("--upsd-port", type=int, default=3493, help="upsd port (default: 3493)")

    return parser


def cmd_server(args: argparse.Namespace) -> None:
    """Run the server setup wizard."""
    print("=== nut-up server setup ===\n")

    # 1. Check NUT installed
    if not is_nut_installed():
        print("NUT is not installed. Installing nut packages...")
        try:
            install_nut_packages()
            print("NUT installed successfully.\n")
        except Exception as e:
            print(f"Failed to install NUT: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("NUT is already installed.\n")

    # 2. Check/backup existing config
    conf_dir = args.conf_dir
    reader = NUTConfigReader(conf_dir)
    writer = NUTConfigWriter(conf_dir)

    if reader.has_existing_config():
        print("Existing NUT config found. Backing up...")
        backups = writer.backup_existing()
        for b in backups:
            print(f"  backed up: {b}")
        print()

    # 3. Scan USB for UPS
    print("Scanning for USB UPS devices...")
    devices = scan_usb()

    if not devices:
        print("No USB UPS devices found.", file=sys.stderr)
        print("Make sure your UPS is connected via USB.", file=sys.stderr)
        sys.exit(1)

    device = devices[0]
    ups_name = args.ups_name or device.get("name", "ups")
    print(f"Found: {device.get('desc', 'Unknown UPS')} (driver: {device['driver']})\n")

    # 4. Generate passwords
    admin_password = secrets.token_urlsafe(16)
    monitor_password = secrets.token_urlsafe(16)

    # 5. Write all configs (always netserver, listen 0.0.0.0)
    ups_entry = {
        "name": ups_name,
        "driver": device["driver"],
        "port": device.get("port", "auto"),
        "desc": device.get("desc", "UPS"),
        "extra": device.get("extra", {}),
    }

    print("Writing NUT configuration files...")
    paths = writer.write_server(
        mode="netserver",
        ups_list=[ups_entry],
        admin_password=admin_password,
        monitor_password=monitor_password,
        listen_addresses=["0.0.0.0"],
    )
    for p in paths:
        print(f"  wrote: {p}")
    print()

    # 6. Save server info to state file
    state = StateManager(args.state_file)
    state.update(
        lambda data: data["server"].update(
            {
                "mode": "netserver",
                "ups_name": ups_name,
                "conf_dir": conf_dir,
                "admin_password": admin_password,
                "monitor_password": monitor_password,
            }
        )
    )
    print(f"State saved to: {args.state_file}\n")

    # 7. Start services unless --no-start
    if not args.no_start:
        print("Starting NUT services...")
        try:
            start_nut_server()
            print("NUT services started.\n")
        except Exception as e:
            print(f"Failed to start NUT services: {e}", file=sys.stderr)
            print("You can start them manually with: nut-up start")

    # 8. Print summary
    print("=== Setup complete ===")
    print(f"  UPS name:   {ups_name}")
    print(f"  Driver:     {device['driver']}")
    print("  Mode:       netserver")
    print("  Listening:  0.0.0.0:3493")
    print(f"  Config dir: {conf_dir}")
    print(f"  State file: {args.state_file}")


def cmd_start(args: argparse.Namespace) -> None:
    """Start all NUT services."""
    print("Starting NUT services...")
    try:
        start_nut_server()
        print("All NUT services started.")
    except Exception as e:
        print(f"Failed to start services: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop all NUT services."""
    print("Stopping NUT services...")
    stop_nut_server()
    print("All NUT services stopped.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show NUT service status."""
    status = nut_server_status()
    print("NUT service status:")
    for unit, state in status.items():
        print(f"  {unit}: {state}")


def cmd_web(args: argparse.Namespace) -> None:
    """Run the web UI in foreground."""
    os.environ["NUT_UP_STATE_FILE"] = str(args.state_file)
    os.environ["NUT_UP_UPSD_HOST"] = args.upsd_host
    os.environ["NUT_UP_UPSD_PORT"] = str(args.upsd_port)

    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is not installed. Install with: pip install uvicorn[standard]", file=sys.stderr
        )
        sys.exit(1)

    print(f"Starting nut-up web UI on {args.host}:{args.port}...")
    uvicorn.run(
        "nut_up.app:create_app",
        host=args.host,
        port=args.port,
        factory=True,
    )


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "server": cmd_server,
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "web": cmd_web,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
