#!/bin/bash
# deploy_to_openwrt.sh - Push compiled artifacts and scripts onto the OpenWrt VM.
#
# Usage:
#   OPENWRT_HOST=192.168.x.1 ./scripts/deploy_to_openwrt.sh
#
# Optional env:
#   OPENWRT_USER (default: root)
#   OPENWRT_PORT (default: 22)
#
# Requires SSH key auth (no password). Set it up once with:
#   ssh-copy-id root@<OpenWrt-IP>
#
# Authentication via password is intentionally NOT supported here to keep
# the script automation-friendly and to discourage typing passwords.

set -euo pipefail

OPENWRT_USER="${OPENWRT_USER:-root}"
OPENWRT_PORT="${OPENWRT_PORT:-22}"

if [ -z "${OPENWRT_HOST:-}" ]; then
    echo "ERROR: set OPENWRT_HOST to the OpenWrt VM IP" >&2
    echo "example: OPENWRT_HOST=192.168.86.10 $0" >&2
    exit 64
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_TARGET="${OPENWRT_USER}@${OPENWRT_HOST}"
SSH_OPTS=(-p "${OPENWRT_PORT}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
SCP_OPTS=(-P "${OPENWRT_PORT}" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)

echo "==> target: ${SSH_TARGET}:${OPENWRT_PORT}"

echo "==> firewall scripts -> /usr/bin/"
scp "${SCP_OPTS[@]}" "${REPO_ROOT}"/firewall-scripts/*.sh "${SSH_TARGET}":/usr/bin/
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
    #"chmod +x /usr/bin/*.sh && sed -i 's/\r\$//' /usr/bin/*.sh"
    "chmod +x /usr/bin/*.sh && sed -i 's/\r//g' /usr/bin/*.sh"

if [ -f "${REPO_ROOT}/traffic-monitor/bin/traffic_monitor.openwrt" ]; then
    echo "==> traffic monitor binary -> /usr/bin/traffic_monitor"
    scp "${SCP_OPTS[@]}" \
        "${REPO_ROOT}/traffic-monitor/bin/traffic_monitor.openwrt" \
        "${SSH_TARGET}":/usr/bin/traffic_monitor
    ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "chmod +x /usr/bin/traffic_monitor"
else
    echo "(skip) traffic-monitor not cross-compiled yet; run 'make -f Makefile.openwrt' in traffic-monitor/ first"
fi

echo "==> backend -> /root/backend/"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p /root/backend"
scp "${SCP_OPTS[@]}" -r "${REPO_ROOT}"/backend/* "${SSH_TARGET}":/root/backend/

if [ -d "${REPO_ROOT}/frontend/dist" ]; then
    echo "==> frontend dist -> /www/app/"
    ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p /www/app && rm -rf /www/app/*"
    scp "${SCP_OPTS[@]}" -r "${REPO_ROOT}"/frontend/dist/* "${SSH_TARGET}":/www/app/
else
    echo "(skip) frontend/dist not built yet; partner B should run 'pnpm build' first"
fi

echo "==> done. on OpenWrt: cd /root/backend && MOCK_MODE=false python3 app.py"
