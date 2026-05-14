#ifndef TRAFFIC_MONITOR_CAPTURE_H
#define TRAFFIC_MONITOR_CAPTURE_H

#include <pcap.h>
#include <signal.h>

typedef struct {
    const char *iface;
    const char *bpf;
    int snaplen;
    volatile sig_atomic_t *stop;
    pcap_t *handle;
} capture_ctx_t;

/* Entry point for the capture pthread. arg must be a capture_ctx_t*.
 * Returns NULL when pcap_loop exits (either via pcap_breakloop or an error). */
void *capture_thread_main(void *arg);

/* Request the capture loop to stop. Safe to call from a signal handler. */
void capture_stop(capture_ctx_t *ctx);

#endif /* TRAFFIC_MONITOR_CAPTURE_H */
