#!/bin/sh
# STUB del_rule.sh - removes a rule by id from $STUB_STATE. Exits 1 if the id
# is absent (matching the real script's "not found" contract). No real
# firewall involved.

set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <ruleId>" >&2
    exit 64
fi

RULE_ID="$1"
STATE="${STUB_STATE:?STUB_STATE not set}"
[ -f "$STATE" ] || { echo "rule not found: $RULE_ID" >&2; exit 1; }

if ! grep -q "^$RULE_ID|" "$STATE"; then
    echo "rule not found: $RULE_ID" >&2
    exit 1
fi

tmp="$STATE.tmp"
grep -v "^$RULE_ID|" "$STATE" > "$tmp" || true
mv "$tmp" "$STATE"

echo "Rule $RULE_ID deleted"
exit 0
