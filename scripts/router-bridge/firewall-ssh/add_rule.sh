#!/bin/sh
# Router-bridge firewall wrapper.
#
# The PC-side Flask backend (MOCK_MODE=false) calls
#   $FIREWALL_SCRIPTS_DIR/<name>.sh <args...>
# via subprocess. On the router these scripts use uci/fw4, which don't exist
# on the PC. So each wrapper here forwards the call over SSH to the SAME-named
# script on the router (/usr/local/bin/<name>.sh), preserving args, stdout,
# stderr and the exit code (1=not found -> backend 404, etc.).
#
# All four wrappers (add_rule/del_rule/list_rules/clear_rules) are identical;
# the remote script name is derived from this file's own name, so point
# FIREWALL_SCRIPTS_DIR at the directory containing them.
#
# Requires:
#   - ROUTER_HOST env var = router IP (e.g. 192.168.1.1)
#   - passwordless SSH key auth from this PC to root@$ROUTER_HOST
#     (set up once: ssh-copy-id root@<router-ip>)
#   - the PC must be able to reach the router (NOT WSL2 default NAT; see README)

set -eu

name="$(basename "$0")"
: "${ROUTER_HOST:?set ROUTER_HOST to the router IP, e.g. ROUTER_HOST=192.168.1.1}"
ROUTER_USER="${ROUTER_USER:-root}"
ROUTER_PORT="${ROUTER_PORT:-22}"

exec ssh -p "$ROUTER_PORT" \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=accept-new \
    "${ROUTER_USER}@${ROUTER_HOST}" \
    /usr/local/bin/"$name" "$@"
