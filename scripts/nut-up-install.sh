#!/usr/bin/env bash
set -euo pipefail

REPO="kgNatx/nut-up"
BRANCH="main"
ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.tar.gz"
INSTALL_DIR="/opt/nut-up"

# --- Check root ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "Error: this script must be run as root (use sudo)." >&2
    exit 1
fi

# --- Check Python 3 + venv ---
if ! command -v python3 &>/dev/null; then
    echo "Python 3 not found. Installing..."
    apt-get update -qq && apt-get install -y -qq python3 python3-venv
fi

# Ensure python3-venv is available (some distros split it out)
if ! python3 -m venv --help &>/dev/null 2>&1; then
    echo "python3-venv not found. Installing..."
    apt-get update -qq && apt-get install -y -qq python3-venv
fi

echo ""
echo "==> Installing nut-up to ${INSTALL_DIR} ..."

# --- Download and extract ---
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "==> Downloading nut-up..."
curl -sL "${ARCHIVE_URL}" -o "${TMP_DIR}/nut-up.tar.gz"

echo "==> Extracting..."
tar -xzf "${TMP_DIR}/nut-up.tar.gz" -C "${TMP_DIR}"

# GitHub archives extract to repo-branch/ directory
SRC_DIR="${TMP_DIR}/nut-up-${BRANCH}"

# --- Install to /opt/nut-up ---
if [[ -d "${INSTALL_DIR}" ]]; then
    echo "==> Existing installation found — upgrading..."
    # Preserve state file if it exists
    if [[ -f "${INSTALL_DIR}/state.json" ]]; then
        cp "${INSTALL_DIR}/state.json" "${TMP_DIR}/state.json.bak"
    fi
    rm -rf "${INSTALL_DIR}"
fi

mkdir -p "${INSTALL_DIR}"
cp -r "${SRC_DIR}/"* "${INSTALL_DIR}/"

# Restore state file
if [[ -f "${TMP_DIR}/state.json.bak" ]]; then
    cp "${TMP_DIR}/state.json.bak" "${INSTALL_DIR}/state.json"
fi

# --- Create venv and install ---
echo "==> Creating virtual environment..."
python3 -m venv "${INSTALL_DIR}/venv"

echo "==> Installing dependencies..."
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip -q
"${INSTALL_DIR}/venv/bin/pip" install "${INSTALL_DIR}" -q

# --- Symlink CLI ---
ln -sf "${INSTALL_DIR}/venv/bin/nut-up" /usr/local/bin/nut-up
echo "==> Installed nut-up CLI to /usr/local/bin/nut-up"

# --- Install systemd unit ---
cp "${INSTALL_DIR}/scripts/nut-up.service" /etc/systemd/system/nut-up.service
systemctl daemon-reload
echo "==> Installed systemd service"

# --- Open firewall port if UFW is active ---
if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
    if ! ufw status | grep -q "3494"; then
        echo "==> Opening port 3494 in UFW..."
        ufw allow 3494/tcp comment "nut-up web UI" >/dev/null
    else
        echo "==> Port 3494 already open in UFW"
    fi
    # NUT upsd port for client enrollment
    if ! ufw status | grep -q "3493"; then
        echo "==> Opening port 3493 in UFW (NUT upsd for clients)..."
        ufw allow 3493/tcp comment "NUT upsd" >/dev/null
    fi
fi

echo ""
echo "============================================"
echo "  nut-up installed successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Connect your UPS via USB"
echo "  2. Run:  sudo nut-up server"
echo "  3. Open: http://$(hostname -I | awk '{print $1}'):3494"
echo ""
