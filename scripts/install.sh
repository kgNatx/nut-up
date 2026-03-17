#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/YOUR_USER/nut-up"
INSTALL_DIR="/opt/nut-up"

# --- Check root ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "Error: this script must be run as root (use sudo)." >&2
    exit 1
fi

# --- Check Python 3 ---
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is not installed." >&2
    echo "Install it with:  apt install python3 python3-venv  (Debian/Ubuntu)" >&2
    echo "                   dnf install python3              (Fedora/RHEL)" >&2
    exit 1
fi

echo "==> Installing nut-up to ${INSTALL_DIR} ..."

# --- Clone or update repo ---
if [[ -d "${INSTALL_DIR}/.git" ]]; then
    echo "==> Existing installation found — pulling latest ..."
    git -C "${INSTALL_DIR}" pull --ff-only
else
    echo "==> Cloning repository ..."
    mkdir -p "${INSTALL_DIR}"
    git clone "${REPO_URL}" "${INSTALL_DIR}"
fi

# --- Create venv and install ---
echo "==> Creating virtual environment ..."
python3 -m venv "${INSTALL_DIR}/venv"

echo "==> Installing nut-up into venv ..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install "${INSTALL_DIR}"

# --- Symlink CLI ---
echo "==> Symlinking CLI to /usr/local/bin/nut-up ..."
ln -sf "${INSTALL_DIR}/venv/bin/nut-up" /usr/local/bin/nut-up

# --- Install systemd unit ---
echo "==> Installing systemd service ..."
cp "${INSTALL_DIR}/scripts/nut-up.service" /etc/systemd/system/nut-up.service
systemctl daemon-reload

echo ""
echo "============================================"
echo "  nut-up installed successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Connect your UPS via USB"
echo "  2. Run the server setup wizard:"
echo "       sudo nut-up server"
echo "  3. Start the web UI:"
echo "       sudo systemctl enable --now nut-up"
echo "  4. Open http://$(hostname -I | awk '{print $1}'):3494"
echo ""
