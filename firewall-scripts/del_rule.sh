#!/bin/sh
# del_rule.sh - Delete a firewall rule by id on OpenWrt (uci / fw4).
#
# Usage: del_rule.sh <ruleId>
#   ruleId : the id returned by add_rule.sh / list_rules.sh, e.g. "webfw-3"
#
# Exit code: 0 deleted, 1 rule not found, 64 usage error, other = failure.
#
# ruleId is validated by the backend (validate_rule_id) before reaching here,
# but it is still only ever used as a uci option value match, never eval'd.

set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <ruleId>" >&2
    exit 64
fi

RULE_ID="$1"

# Find the uci section whose name option equals exactly this rule id.
FOUND=""
for sec in $(uci -q show firewall \
    | sed -n "s/^firewall\.\([^.]*\)\.name='$RULE_ID'\$/\1/p"); do
    FOUND="$sec"
done

if [ -z "$FOUND" ]; then
    echo "rule not found: $RULE_ID" >&2
    exit 1
fi

uci delete firewall."$FOUND"
uci commit firewall
fw4 reload >/dev/null 2>&1

echo "Rule $RULE_ID deleted"
exit 0
