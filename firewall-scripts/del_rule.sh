#!/bin/sh
# del_rule.sh - Delete a firewall rule by ID on OpenWrt.
#
# Usage: del_rule.sh <ruleId>
#
# Exit code: 0 on success, 1 if rule not found, other non-zero on failure.

set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <ruleId>" >&2
    exit 64
fi

RULE_ID="$1"

echo "TODO: Phase 3 will implement del_rule via fw4/nft."
echo "received args: ruleId=$RULE_ID"
exit 0
