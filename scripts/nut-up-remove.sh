#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/nut-up"

# --- Check root ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "Error: this script must be run as root (use sudo)." >&2
    exit 1
fi

echo ""
echo "==> Removing nut-up..."

# --- Stop and disable services ---
if systemctl is-active --quiet nut-up.service 2>/dev/null; then
    echo "==> Stopping nut-up web UI..."
    systemctl stop nut-up.service
fi
if systemctl is-enabled --quiet nut-up.service 2>/dev/null; then
    systemctl disable nut-up.service
fi
if [[ -f /etc/systemd/system/nut-up.service ]]; then
    echo "==> Removing systemd service..."
    rm -f /etc/systemd/system/nut-up.service
    systemctl daemon-reload
fi

# --- Remove CLI symlink ---
if [[ -L /usr/local/bin/nut-up ]]; then
    echo "==> Removing CLI symlink..."
    rm -f /usr/local/bin/nut-up
fi

# --- Remove install directory ---
if [[ -d "${INSTALL_DIR}" ]]; then
    echo "==> Removing ${INSTALL_DIR}..."
    rm -rf "${INSTALL_DIR}"
fi

echo ""
echo "============================================"
echo "  nut-up removed."
echo "============================================"
echo ""
echo "Note: NUT itself (nut-server, nut-client) was NOT removed."
echo "      NUT config files in /etc/nut/ were NOT touched."
echo "      To remove NUT:  apt remove nut nut-server nut-client"
echo ""
