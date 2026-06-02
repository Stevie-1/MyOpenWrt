#!/bin/sh
# STUB list_rules.sh - emits the rules in $STUB_STATE as JSON matching
# docs/api.md. No real firewall involved.

set -eu

STATE="${STUB_STATE:?STUB_STATE not set}"
[ -f "$STATE" ] || { echo '{"rules":[]}'; exit 0; }

printf '{"rules":['
first=1
while IFS='|' read -r id proto src dst port action; do
    [ -n "$id" ] || continue
    if [ "$first" -eq 1 ]; then
        first=0
    else
        printf ','
    fi
    printf '{"id":"%s","proto":"%s","src":"%s","dst":"%s","port":%s,"action":"%s"}' \
        "$id" "$proto" "$src" "$dst" "${port:-0}" "$action"
done < "$STATE"
printf ']}\n'
exit 0
