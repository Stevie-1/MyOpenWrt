#!/bin/bash
# start_backend.sh - start the PC-side Flask backend wired to the real router.
#
# Run this on the PC that can reach the router over SSH (see README about
# WSL2 networking). It assumes:
#   - pull_traffic.sh is already running (or will be started by you), writing
#     to $TRAFFIC_JSON_PATH
#   - SSH key auth to root@$ROUTER_HOST is set up
#
# Usage:
#   ROUTER_HOST=192.168.1.1 ./scripts/router-bridge/start_backend.sh

set -euo pipefail

: "${ROUTER_HOST:?set ROUTER_HOST to the router IP, e.g. ROUTER_HOST=192.168.1.1}"
export ROUTER_HOST
export ROUTER_USER="${ROUTER_USER:-root}"
export ROUTER_PORT="${ROUTER_PORT:-22}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

export MOCK_MODE=false
export TRAFFIC_JSON_PATH="${TRAFFIC_JSON_PATH:-/tmp/router-traffic.json}"
export FIREWALL_SCRIPTS_DIR="${FIREWALL_SCRIPTS_DIR:-${REPO_ROOT}/scripts/router-bridge/firewall-ssh}"

echo "==> ROUTER_HOST=${ROUTER_HOST}"
echo "==> TRAFFIC_JSON_PATH=${TRAFFIC_JSON_PATH}"
echo "==> FIREWALL_SCRIPTS_DIR=${FIREWALL_SCRIPTS_DIR}"
echo "==> reminder: run pull_traffic.sh in another terminal so traffic data flows"

cd "${REPO_ROOT}/backend"
exec python3 app.py
