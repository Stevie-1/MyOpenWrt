#!/bin/sh
# list_rules.sh - List the rules this app created on OpenWrt, as JSON.
#
# Usage: list_rules.sh
#
# Output (stdout): JSON matching docs/api.md firewall rule schema:
#   {"rules":[{"id":"webfw-1","proto":"tcp","src":"any","dst":"192.168.1.1",
#              "port":80,"action":"drop"}]}
#
# Only rules whose name starts with "webfw-" are listed; system/default rules
# are left untouched. JSON is hand-rolled (no jq dependency); all values are
# constrained (validated IPs/proto/port/action) so no escaping is required.
#
# Exit code: 0 on success.

set -u

# uci section ids (e.g. cfg0a1b2c) for our webfw- rules.
sections() {
    uci -q show firewall \
        | sed -n "s/^firewall\.\([^.]*\)\.name='webfw-[0-9]\{1,\}'\$/\1/p"
}

get() {
    # get <section> <option> <default>
    val="$(uci -q get firewall."$1"."$2" 2>/dev/null || true)"
    if [ -z "$val" ]; then
        echo "$3"
    else
        echo "$val"
    fi
}

printf '{"rules":['
first=1
for sec in $(sections); do
    id="$(get "$sec" name "")"
    proto="$(get "$sec" proto other)"
    target="$(get "$sec" target DROP)"
    action="$(echo "$target" | tr '[:upper:]' '[:lower:]')"
    src="$(get "$sec" src_ip any)"
    dst="$(get "$sec" dest_ip any)"
    port="$(get "$sec" dest_port 0)"

    if [ "$first" -eq 1 ]; then
        first=0
    else
        printf ','
    fi
    printf '{"id":"%s","proto":"%s","src":"%s","dst":"%s","port":%s,"action":"%s"}' \
        "$id" "$proto" "$src" "$dst" "$port" "$action"
done
printf ']}\n'
exit 0
