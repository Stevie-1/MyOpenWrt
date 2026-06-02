#!/bin/sh
# STUB add_rule.sh - emulates the OpenWrt add_rule.sh contract on a dev box
# WITHOUT touching any real firewall. State lives in the file pointed to by
# $STUB_STATE (one rule per line: id|proto|src|dst|port|action).
#
# Used only by test/test_firewall_real.py to exercise the backend's real
# (non-mock) subprocess path on WSL2/CI where uci/fw4 don't exist.

set -eu

if [ "$#" -ne 5 ]; then
    echo "usage: $0 <proto> <src> <dst> <port> <action>" >&2
    exit 64
fi

PROTO="$1"; SRC="$2"; DST="$3"; PORT="$4"; ACTION="$5"
STATE="${STUB_STATE:?STUB_STATE not set}"
touch "$STATE"

max=0
while IFS='|' read -r id _rest; do
    seq="${id#webfw-}"
    case "$seq" in
        ''|*[!0-9]*) : ;;
        *) [ "$seq" -gt "$max" ] && max="$seq" ;;
    esac
done < "$STATE"

SEQ=$((max + 1))
RULE_ID="webfw-$SEQ"
echo "$RULE_ID|$PROTO|$SRC|$DST|$PORT|$ACTION" >> "$STATE"

echo "ruleId=$RULE_ID"
echo "Rule $RULE_ID added"
exit 0
