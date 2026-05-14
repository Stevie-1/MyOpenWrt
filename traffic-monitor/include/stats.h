#ifndef TRAFFIC_MONITOR_STATS_H
#define TRAFFIC_MONITOR_STATS_H

#include <stdint.h>
#include <stddef.h>

/* Sliding window length in seconds; covers the 40s requirement and includes
 * smaller windows (2s / 10s) as sub-sums. */
#define STATS_WINDOW_SECONDS 40

#define STATS_PROTO_TCP    6
#define STATS_PROTO_UDP    17
#define STATS_PROTO_ICMP   1
#define STATS_PROTO_OTHER  0xFF

/* 5-tuple key. IPs are stored as network-byte-order uint32_t for
 * compact hashing; convert via inet_ntop on output. Ports are host order. */
typedef struct {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    uint8_t  proto;
} flow_key_t;

/* Snapshot row returned by stats_snapshot. Self-contained for JSON output. */
typedef struct {
    flow_key_t key;
    uint64_t rx_bytes;
    uint64_t tx_bytes;
    uint64_t peak;
    uint64_t avg2s;
    uint64_t avg10s;
    uint64_t avg40s;
} flow_snapshot_t;

void stats_init(void);
void stats_destroy(void);

/* Record bytes for a flow. is_tx selects rx vs tx counter.
 * Called from the capture thread for every packet; thread-safe. */
void stats_record(const flow_key_t *key, size_t bytes, int is_tx);

/* Advance the per-flow ring buffer by one slot.
 * Called from the main thread once per second; thread-safe. */
void stats_tick(void);

/* Copy current snapshots into `out`. Returns number of rows written
 * (clamped to `out_max`). Thread-safe. */
size_t stats_snapshot(flow_snapshot_t *out, size_t out_max);

#endif /* TRAFFIC_MONITOR_STATS_H */
