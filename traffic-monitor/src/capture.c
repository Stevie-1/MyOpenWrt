/*
 * capture.c — libpcap loop + IPv4 packet parser.
 *
 * Responsibilities:
 *   1. Open the requested interface in promiscuous mode.
 *   2. Compile/install the user-supplied BPF filter (default: "ip").
 *   3. For each captured frame, parse Ethernet + IPv4 + L4 to build a
 *      flow_key_t, then push the byte count into stats.
 *
 * Limitations (intentional, scope-of-lab):
 *   - IPv4 only. IPv6 packets are silently skipped — adding them only means
 *     a new key layout.
 *   - VLAN-tagged frames are not handled.
 *   - "is_tx" is heuristic: we don't know which IP is local at this layer,
 *     so we always count toward rx_bytes. The 5-tuple key already keeps
 *     directions separate; downstream code can sum both directions to
 *     get full-duplex byte counts.
 */

#include "capture.h"
#include "stats.h"

#include <sys/types.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <pcap.h>
#include <stdio.h>
#include <string.h>

/* Ethernet header is fixed-size (no VLAN handling). */
#define ETH_HDR_LEN 14
#define ETHERTYPE_IPV4 0x0800

struct ipv4_hdr_min {
    uint8_t  vihl;       /* version (4 bits) + IHL (4 bits) */
    uint8_t  tos;
    uint16_t total_len;
    uint16_t id;
    uint16_t frag;
    uint8_t  ttl;
    uint8_t  proto;
    uint16_t checksum;
    uint32_t src;
    uint32_t dst;
};

static void on_packet(u_char *user, const struct pcap_pkthdr *h, const u_char *bytes) {
    (void)user;
    if (h->caplen < ETH_HDR_LEN + sizeof(struct ipv4_hdr_min)) return;

    /* Ethertype lives at offset 12 in the Ethernet header, network order. */
    uint16_t ethertype;
    memcpy(&ethertype, bytes + 12, sizeof(ethertype));
    if (ntohs(ethertype) != ETHERTYPE_IPV4) return;

    const u_char *ip = bytes + ETH_HDR_LEN;
    uint8_t vihl = ip[0];
    if ((vihl >> 4) != 4) return;
    size_t ihl = (size_t)(vihl & 0x0F) * 4;
    if (ihl < 20 || h->caplen < ETH_HDR_LEN + ihl) return;

    struct ipv4_hdr_min iph;
    memcpy(&iph, ip, sizeof(iph));

    flow_key_t key = {
        .src_ip   = iph.src,
        .dst_ip   = iph.dst,
        .src_port = 0,
        .dst_port = 0,
        .proto    = iph.proto,
    };

    const u_char *l4 = ip + ihl;
    size_t l4_avail = (h->caplen > ETH_HDR_LEN + ihl)
        ? h->caplen - ETH_HDR_LEN - ihl : 0;

    switch (iph.proto) {
        case STATS_PROTO_TCP:
        case STATS_PROTO_UDP:
            if (l4_avail >= 4) {
                uint16_t sp, dp;
                memcpy(&sp, l4 + 0, 2);
                memcpy(&dp, l4 + 2, 2);
                key.src_port = ntohs(sp);
                key.dst_port = ntohs(dp);
            }
            break;
        case STATS_PROTO_ICMP:
        default:
            /* No L4 ports for ICMP / other. The 5-tuple key still works
             * with ports = 0. */
            break;
    }

    /* h->len is the full on-the-wire size including the Ethernet header,
     * which matches the "rxBytes / txBytes" intent of the API spec. */
    stats_record(&key, h->len, /* is_tx = */ 0);
}

void *capture_thread_main(void *arg) {
    capture_ctx_t *ctx = (capture_ctx_t *)arg;
    if (!ctx || !ctx->handle) return NULL;

    pcap_loop(ctx->handle, /*count=*/-1, on_packet, NULL);
    /* Returning means pcap_breakloop was called or an error occurred;
     * either way the main thread is responsible for pcap_close. */
    return NULL;
}

void capture_stop(capture_ctx_t *ctx) {
    if (ctx && ctx->handle) {
        pcap_breakloop(ctx->handle);
    }
}
