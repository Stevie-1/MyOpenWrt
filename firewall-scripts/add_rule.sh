#!/bin/sh
# add_rule.sh - Add a firewall rule on OpenWrt 24.10 (fw4 / nftables) via uci.
#
# Usage: add_rule.sh <proto> <src> <dst> <port> <action>
#   proto  : tcp | udp | icmp
#   src    : IPv4 or CIDR or "any"
#   dst    : IPv4 or CIDR or "any"
#   port   : 1-65535 (ignored for icmp)
#   action : accept | reject | drop
#
# Output (stdout): a "ruleId=<id>" line the backend parses, plus a human line.
# Exit code: 0 success, 64 usage error, other = uci/fw4 failure.
#
# Inputs are pre-validated by the Flask backend (_validators.py) but this
# script still treats them as untrusted: every value is passed as a uci
# option value only, never eval'd or concatenated into a command.

set -eu

if [ "$#" -ne 5 ]; then
    echo "usage: $0 <proto> <src> <dst> <port> <action>" >&2
    exit 64
fi

PROTO="$1"
SRC="$2"
DST="$3"
PORT="$4"
ACTION="$5"

# Highest existing webfw-<n> sequence number, so the next id is monotonic.
next_seq() {
    max=0
    for n in $(uci -q show firewall \
        | sed -n "s/^firewall\.[^.]*\.name='webfw-\([0-9]\{1,\}\)'\$/\1/p"); do
        if [ "$n" -gt "$max" ]; then
            max="$n"
        fi
    done
    echo $((max + 1))
}

SEQ="$(next_seq)"
RULE_ID="webfw-$SEQ"

# uci target option is upper-case (ACCEPT / REJECT / DROP). (Checked wrong by Stevie-1)
# TARGET="$(echo "$ACTION" | tr '[:lower:]' '[:upper:]')" 

# Remove any trailing newline or carriage return characters from ACTION before converting to uppercase, to ensure the TARGET value is clean and valid for uci.
TARGET="$(echo "$ACTION" | tr -d '\r\n' | tr 'a-z' 'A-Z')"

SEC="$(uci add firewall rule)"
uci set firewall."$SEC".name="$RULE_ID"
uci set firewall."$SEC".src='lan' #  (Zone: lan) It's Safer.
uci set firewall."$SEC".family='ipv4'
uci set firewall."$SEC".proto="$PROTO"
uci set firewall."$SEC".target="$TARGET"

if [ "$SRC" != "any" ]; then
    uci set firewall."$SEC".src_ip="$SRC"
fi
if [ "$DST" != "any" ]; then
    uci set firewall."$SEC".dest_ip="$DST"
fi
if [ "$PROTO" = "tcp" ] || [ "$PROTO" = "udp" ]; then
    uci set firewall."$SEC".dest_port="$PORT"
fi

uci commit firewall
fw4 reload >/dev/null 2>&1

echo "ruleId=$RULE_ID"
echo "Rule $RULE_ID added"
exit 0
