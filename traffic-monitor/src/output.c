/*
 * output.c — serialize the current stats snapshot to JSON.
 *
 * The on-disk file is consumed by the Python backend (see
 * backend/api/traffic.py); both `{"items": [...]}` and a bare array are
 * accepted on that side, but we emit the wrapped form to make the file
 * self-documenting and easy to eyeball with `cat`.
 *
 * Atomicity: we write to "<path>.tmp" and then rename(2) it over `path`.
 * On POSIX rename within the same directory is atomic, so the backend will
 * never observe a half-written JSON.
 */

#include "output.h"
#include "stats.h"

#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#define SNAPSHOT_MAX 4096u

static const char *proto_name(uint8_t p) {
    switch (p) {
        case STATS_PROTO_TCP:  return "tcp";
        case STATS_PROTO_UDP:  return "udp";
        case STATS_PROTO_ICMP: return "icmp";
        default:               return "other";
    }
}

static int write_row(FILE *f, const flow_snapshot_t *r, int first) {
    char src_ip[INET_ADDRSTRLEN] = {0};
    char dst_ip[INET_ADDRSTRLEN] = {0};
    struct in_addr s = { .s_addr = r->key.src_ip };
    struct in_addr d = { .s_addr = r->key.dst_ip };
    if (!inet_ntop(AF_INET, &s, src_ip, sizeof(src_ip))) {
        snprintf(src_ip, sizeof(src_ip), "0.0.0.0");
    }
    if (!inet_ntop(AF_INET, &d, dst_ip, sizeof(dst_ip))) {
        snprintf(dst_ip, sizeof(dst_ip), "0.0.0.0");
    }
    return fprintf(f,
        "%s\n    {"
        "\"srcIp\":\"%s\","
        "\"dstIp\":\"%s\","
        "\"srcPort\":%u,"
        "\"dstPort\":%u,"
        "\"proto\":\"%s\","
        "\"rxBytes\":%llu,"
        "\"txBytes\":%llu,"
        "\"peak\":%llu,"
        "\"avg2s\":%llu,"
        "\"avg10s\":%llu,"
        "\"avg40s\":%llu}",
        first ? "" : ",",
        src_ip, dst_ip,
        (unsigned)r->key.src_port,
        (unsigned)r->key.dst_port,
        proto_name(r->key.proto),
        (unsigned long long)r->rx_bytes,
        (unsigned long long)r->tx_bytes,
        (unsigned long long)r->peak,
        (unsigned long long)r->avg2s,
        (unsigned long long)r->avg10s,
        (unsigned long long)r->avg40s);
}

int output_write_json(const char *path) {
    if (!path) { errno = EINVAL; return -1; }

    flow_snapshot_t *rows = calloc(SNAPSHOT_MAX, sizeof(*rows));
    if (!rows) return -1;
    size_t n = stats_snapshot(rows, SNAPSHOT_MAX);

    size_t tmp_len = strlen(path) + 5; /* ".tmp" + NUL */
    char *tmp_path = malloc(tmp_len);
    if (!tmp_path) { free(rows); return -1; }
    snprintf(tmp_path, tmp_len, "%s.tmp", path);

    FILE *f = fopen(tmp_path, "w");
    if (!f) { free(tmp_path); free(rows); return -1; }

    struct timeval tv;
    gettimeofday(&tv, NULL);
    long long ts_ms = (long long)tv.tv_sec * 1000LL + tv.tv_usec / 1000LL;

    fprintf(f, "{\n  \"ts\": %lld,\n  \"items\": [", ts_ms);
    for (size_t i = 0; i < n; ++i) {
        write_row(f, &rows[i], i == 0);
    }
    fprintf(f, "%s]\n}\n", n ? "\n  " : "");

    int err = ferror(f);
    if (fclose(f) != 0) err = 1;
    if (err) {
        unlink(tmp_path);
        free(tmp_path); free(rows);
        return -1;
    }

    if (rename(tmp_path, path) != 0) {
        unlink(tmp_path);
        free(tmp_path); free(rows);
        return -1;
    }

    free(tmp_path);
    free(rows);
    return 0;
}
