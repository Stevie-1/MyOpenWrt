#!/bin/sh
# STUB clear_rules.sh - empties $STUB_STATE. No real firewall involved.

set -eu

STATE="${STUB_STATE:?STUB_STATE not set}"
n=0
if [ -f "$STATE" ]; then
    n="$(grep -c '|' "$STATE" || true)"
    : > "$STATE"
fi

echo "Cleared $n rules"
exit 0
