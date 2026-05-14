#!/bin/sh
# list_rules.sh - List all custom firewall rules on OpenWrt, as JSON.
#
# Usage: list_rules.sh
#
# Output (stdout): JSON object matching docs/api.md firewall rule schema:
#   {"rules":[{"id":"rule-1","proto":"tcp","src":"...","dst":"...","port":80,"action":"drop"}]}
#
# Exit code: 0 on success, non-zero on failure.

set -eu

if [ "$#" -ne 0 ]; then
    echo "usage: $0" >&2
    exit 64
fi

echo "TODO: Phase 3 will implement list_rules via fw4/nft."
echo '{"rules":[]}'
exit 0
