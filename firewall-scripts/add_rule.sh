#!/bin/sh
# add_rule.sh - Add a firewall rule on OpenWrt 24.10 (fw4 / nftables).
#
# Usage: add_rule.sh <proto> <src> <dst> <port> <action>
#   proto  : tcp | udp | icmp
#   src    : IPv4 or CIDR or "any"
#   dst    : IPv4 or CIDR or "any"
#   port   : 1-65535 (ignored for icmp)
#   action : accept | reject | drop
#
# Exit code: 0 on success, non-zero on failure.
# Output: stdout informational; stderr error.
#
# Phase 3 will replace the TODO body with actual `nft add rule` / `uci`
# commands. Inputs are guaranteed pre-validated by the Flask backend
# (_validators.py); this script must still treat them as untrusted and
# never use them with eval or string-concatenated commands.

set -eu

if [ "$#" -ne 5 ]; then
    echo "usage: $0 <proto> <src> <dst> <port> <action>" >&2
    exit 64
fi

PROTO="$1"
SRC="$2"
DST="$3"
PORT="$4"
ACTION="$5"

echo "TODO: Phase 3 will implement add_rule via fw4/nft."
echo "received args: proto=$PROTO src=$SRC dst=$DST port=$PORT action=$ACTION"
exit 0
