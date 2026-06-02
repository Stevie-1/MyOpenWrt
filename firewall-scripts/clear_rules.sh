#!/bin/sh
# clear_rules.sh - Remove every rule this app created on OpenWrt (uci / fw4).
#
# Usage: clear_rules.sh
#
# Only "webfw-" rules are removed; system/default rules are left intact.
# Exit code: 0 on success, other = uci/fw4 failure.

set -eu

# Deleting a section shifts the remaining section ids, so re-query and take
# the first match each iteration until none remain.
n=0
while :; do
    sec="$(uci -q show firewall \
        | sed -n "s/^firewall\.\([^.]*\)\.name='webfw-[0-9]\{1,\}'\$/\1/p" \
        | head -n 1)"
    if [ -z "$sec" ]; then
        break
    fi
    uci delete firewall."$sec"
    n=$((n + 1))
done

uci commit firewall
fw4 reload >/dev/null 2>&1

echo "Cleared $n rules"
exit 0
