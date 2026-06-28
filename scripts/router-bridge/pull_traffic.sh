#!/bin/sh
# pull_traffic.sh - continuously copy the router's /tmp/traffic.json to the PC
# so the PC-side Flask backend (TRAFFIC_JSON_PATH) can serve real data.
#
# The router runs traffic_monitor writing /tmp/traffic.json once per second;
# this loop pulls it to a local file atomically (tmp + mv) at the same cadence.
#
# Usage:
#   ROUTER_HOST=192.168.1.1 ./pull_traffic.sh [local_out_path]
# Then start the backend with TRAFFIC_JSON_PATH pointing at the same path:
#   MOCK_MODE=false TRAFFIC_JSON_PATH=/tmp/router-traffic.json \
#   FIREWALL_SCRIPTS_DIR=<repo>/scripts/router-bridge/firewall-ssh \
#   ROUTER_HOST=192.168.1.1 python app.py
#
# Requires passwordless SSH key auth from this PC to root@$ROUTER_HOST.

set -eu

: "${ROUTER_HOST:?set ROUTER_HOST to the router IP, e.g. ROUTER_HOST=192.168.1.1}"
ROUTER_USER="${ROUTER_USER:-root}"
ROUTER_PORT="${ROUTER_PORT:-22}"
REMOTE_PATH="${REMOTE_PATH:-/tmp/traffic.json}"
OUT="${1:-/tmp/router-traffic.json}"
INTERVAL="${INTERVAL:-1}"

echo "pulling ${ROUTER_USER}@${ROUTER_HOST}:${REMOTE_PATH} -> ${OUT} every ${INTERVAL}s (Ctrl-C to stop)"

while :; do
    if ssh -p "$ROUTER_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
        "${ROUTER_USER}@${ROUTER_HOST}" cat "$REMOTE_PATH" > "${OUT}.tmp" 2>/dev/null; then
        mv "${OUT}.tmp" "$OUT"
    else
        echo "warn: failed to read ${REMOTE_PATH} from router (is traffic_monitor running?)" >&2
        rm -f "${OUT}.tmp"
    fi
    sleep "$INTERVAL"
done
