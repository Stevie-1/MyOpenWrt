#!/bin/sh
# clear_rules.sh - Remove every custom firewall rule on OpenWrt.
#
# Usage: clear_rules.sh
#
# Exit code: 0 on success, non-zero on failure.

set -eu

if [ "$#" -ne 0 ]; then
    echo "usage: $0" >&2
    exit 64
fi

echo "TODO: Phase 3 will implement clear_rules via fw4/nft."
exit 0
