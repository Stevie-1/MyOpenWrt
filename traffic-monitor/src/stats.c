/*
 * stats.c — per-flow counters with sliding window.
 *
 * Data model:
 *   - Open-addressed hash table keyed by the 5-tuple (FNV-1a 64).
 *   - Each entry owns a 40-slot ring buffer (one second per slot).
 *   - The capture thread accumulates into the *current* slot.
 *   - A 1Hz ticker (called from main) advances the cursor and zeroes the
 *     slot that is about to be overwritten.
 *   - A reader (output thread) takes a snapshot under the table mutex; per
 *     row, the sums for the last 2 / 10 / 40 slots are computed.
 *
 * Locking: a single coarse pthread_mutex_t covers the table and every entry.
 * For the expected flow count (hundreds to low thousands) and 1Hz cadence
 * this is plenty; it keeps the implementation small and easy to audit.
 */

#include "stats.h"

#include <pthread.h>
#include <stdlib.h>
#include <string.h>

#define STATS_TABLE_CAP   2048u

typedef struct {
    flow_key_t key;
    uint8_t    used;
    uint64_t   rx_bytes;
    uint64_t   tx_bytes;
    uint64_t   peak;
    /* Rolling per-second totals (rx+tx). cursor points at the slot being
     * filled right now; slot at (cursor - n) holds the totals from n
     * seconds ago. */
    uint64_t   slots[STATS_WINDOW_SECONDS];
} flow_entry_t;

static flow_entry_t  g_table[STATS_TABLE_CAP];
static size_t        g_used;
static unsigned      g_cursor;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;

static uint64_t fnv1a_64(const void *data, size_t n) {
    const uint8_t *p = (const uint8_t *)data;
    uint64_t h = 1469598103934665603ull;
    for (size_t i = 0; i < n; ++i) {
        h ^= (uint64_t)p[i];
        h *= 1099511628211ull;
    }
    return h;
}

static int key_equal(const flow_key_t *a, const flow_key_t *b) {
    return a->src_ip   == b->src_ip   &&
           a->dst_ip   == b->dst_ip   &&
           a->src_port == b->src_port &&
           a->dst_port == b->dst_port &&
           a->proto    == b->proto;
}

/* Locate (or insert) the entry for `key`. Returns NULL only when the table
 * is completely full; in practice STATS_TABLE_CAP is chosen larger than
 * any realistic flow count for this lab. */
static flow_entry_t *find_or_insert(const flow_key_t *key) {
    uint64_t h = fnv1a_64(key, sizeof(*key));
    size_t  i = (size_t)(h % STATS_TABLE_CAP);
    for (size_t probe = 0; probe < STATS_TABLE_CAP; ++probe) {
        flow_entry_t *e = &g_table[i];
        if (!e->used) {
            e->used = 1;
            e->key  = *key;
            e->rx_bytes = e->tx_bytes = e->peak = 0;
            memset(e->slots, 0, sizeof(e->slots));
            g_used++;
            return e;
        }
        if (key_equal(&e->key, key)) {
            return e;
        }
        i = (i + 1u) % STATS_TABLE_CAP;
    }
    return NULL;
}

void stats_init(void) {
    pthread_mutex_lock(&g_lock);
    memset(g_table, 0, sizeof(g_table));
    g_used = 0;
    g_cursor = 0;
    pthread_mutex_unlock(&g_lock);
}

void stats_destroy(void) {
    pthread_mutex_lock(&g_lock);
    memset(g_table, 0, sizeof(g_table));
    g_used = 0;
    pthread_mutex_unlock(&g_lock);
}

void stats_record(const flow_key_t *key, size_t bytes, int is_tx) {
    if (bytes == 0) return;
    pthread_mutex_lock(&g_lock);
    flow_entry_t *e = find_or_insert(key);
    if (e) {
        if (is_tx) e->tx_bytes += bytes;
        else       e->rx_bytes += bytes;
        e->slots[g_cursor] += bytes;
        if (e->slots[g_cursor] > e->peak) e->peak = e->slots[g_cursor];
    }
    pthread_mutex_unlock(&g_lock);
}

void stats_tick(void) {
    pthread_mutex_lock(&g_lock);
    /* Advance to the next slot and clear it; the freshly-zeroed slot
     * becomes the "now" bucket and the slot we just left becomes
     * "1 second ago". */
    g_cursor = (g_cursor + 1u) % STATS_WINDOW_SECONDS;
    for (size_t i = 0; i < STATS_TABLE_CAP; ++i) {
        if (g_table[i].used) {
            g_table[i].slots[g_cursor] = 0;
        }
    }
    pthread_mutex_unlock(&g_lock);
}

/* Sum the last `seconds` slots ending at (cursor - 1), i.e. excluding the
 * currently-filling bucket so the value is a stable "completed window". */
static uint64_t window_sum(const flow_entry_t *e, unsigned cursor, unsigned seconds) {
    uint64_t sum = 0;
    for (unsigned s = 1; s <= seconds; ++s) {
        unsigned idx = (cursor + STATS_WINDOW_SECONDS - s) % STATS_WINDOW_SECONDS;
        sum += e->slots[idx];
    }
    return sum;
}

size_t stats_snapshot(flow_snapshot_t *out, size_t out_max) {
    if (!out || out_max == 0) return 0;
    size_t n = 0;
    pthread_mutex_lock(&g_lock);
    unsigned cursor = g_cursor;
    for (size_t i = 0; i < STATS_TABLE_CAP && n < out_max; ++i) {
        const flow_entry_t *e = &g_table[i];
        if (!e->used) continue;
        flow_snapshot_t *row = &out[n++];
        row->key      = e->key;
        row->rx_bytes = e->rx_bytes;
        row->tx_bytes = e->tx_bytes;
        row->peak     = e->peak;
        row->avg2s    = window_sum(e, cursor, 2)  / 2u;
        row->avg10s   = window_sum(e, cursor, 10) / 10u;
        row->avg40s   = window_sum(e, cursor, 40) / 40u;
    }
    pthread_mutex_unlock(&g_lock);
    return n;
}
