/*
 * main.c — CLI, signal handling, and thread orchestration.
 *
 * Layout:
 *   - main thread: parses CLI, opens pcap, spawns the capture thread, then
 *     loops on a 1-second tick that calls stats_tick() and
 *     output_write_json().
 *   - capture thread: runs pcap_loop and feeds stats_record().
 *
 * Termination: SIGINT/SIGTERM set a flag that both loops poll. The capture
 * loop is also nudged via pcap_breakloop so it returns promptly.
 */

#include "capture.h"
#include "output.h"
#include "stats.h"

#include <arpa/inet.h>
#include <getopt.h>
#include <pcap.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define VERSION_STR "0.1.0"

static volatile sig_atomic_t g_stop = 0;
static capture_ctx_t *g_capture_ctx = NULL;

static void on_signal(int sig) {
    (void)sig;
    g_stop = 1;
    if (g_capture_ctx) capture_stop(g_capture_ctx);
}

static void print_usage(const char *argv0) {
    fprintf(stderr,
        "traffic_monitor " VERSION_STR " — per-flow traffic stats via libpcap\n"
        "Usage: %s [options]\n"
        "  -i, --iface IFACE     network interface (default: any)\n"
        "  -f, --filter EXPR     BPF filter expression (default: \"ip\")\n"
        "  -o, --output PATH     JSON output path (default: /tmp/traffic.json)\n"
        "  -s, --snaplen N       pcap snaplen bytes (default: 96)\n"
        "  -t, --interval MS     write/tick interval (default: 1000)\n"
        "  -h, --help            show this help and exit\n"
        "      --version         print version and exit\n"
        "      --self-test       write a synthetic JSON snapshot to --output and exit\n"
        "                        (does not require capture permissions; for CI/tests)\n",
        argv0);
}

/* Inject a couple of synthetic flows so the JSON schema can be exercised
 * without needing CAP_NET_RAW. Used by --self-test. */
static int run_self_test(const char *out_path) {
    stats_init();

    flow_key_t k1 = {
        .src_ip   = inet_addr("192.168.1.10"),
        .dst_ip   = inet_addr("8.8.8.8"),
        .src_port = 54321,
        .dst_port = 443,
        .proto    = STATS_PROTO_TCP,
    };
    flow_key_t k2 = {
        .src_ip   = inet_addr("192.168.1.10"),
        .dst_ip   = inet_addr("1.1.1.1"),
        .src_port = 50000,
        .dst_port = 53,
        .proto    = STATS_PROTO_UDP,
    };
    flow_key_t k3 = {
        .src_ip   = inet_addr("192.168.1.10"),
        .dst_ip   = inet_addr("8.8.4.4"),
        .src_port = 0,
        .dst_port = 0,
        .proto    = STATS_PROTO_ICMP,
    };
    for (int s = 0; s < 5; ++s) {
        stats_record(&k1, 1500, 0);
        stats_record(&k1, 500,  1);
        stats_record(&k2, 200,  0);
        stats_record(&k3, 84,   0);
        stats_tick();
    }

    int rc = output_write_json(out_path);
    stats_destroy();
    if (rc != 0) { perror("output_write_json"); return 1; }
    fprintf(stderr, "self-test: wrote %s\n", out_path);
    return 0;
}

static void ms_sleep(long ms) {
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

int main(int argc, char **argv) {
    const char *iface    = "any";
    const char *bpf_expr = "ip";
    const char *out_path = "/tmp/traffic.json";
    int   snaplen        = 96;
    long  interval_ms    = 1000;

    int self_test = 0;
    static struct option long_opts[] = {
        {"iface",     required_argument, 0, 'i'},
        {"filter",    required_argument, 0, 'f'},
        {"output",    required_argument, 0, 'o'},
        {"snaplen",   required_argument, 0, 's'},
        {"interval",  required_argument, 0, 't'},
        {"help",      no_argument,       0, 'h'},
        {"version",   no_argument,       0,  1 },
        {"self-test", no_argument,       0,  2 },
        {0, 0, 0, 0}
    };
    int c;
    while ((c = getopt_long(argc, argv, "i:f:o:s:t:h", long_opts, NULL)) != -1) {
        switch (c) {
            case 'i': iface = optarg; break;
            case 'f': bpf_expr = optarg; break;
            case 'o': out_path = optarg; break;
            case 's': snaplen = atoi(optarg); break;
            case 't': interval_ms = atol(optarg); break;
            case 'h': print_usage(argv[0]); return 0;
            case 1:   printf("%s\n", VERSION_STR); return 0;
            case 2:   self_test = 1; break;
            default:  print_usage(argv[0]); return 2;
        }
    }
    if (self_test) return run_self_test(out_path);
    if (snaplen < 64) snaplen = 64;
    if (interval_ms < 100) interval_ms = 100;

    signal(SIGINT,  on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGPIPE, SIG_IGN);

    stats_init();

    char errbuf[PCAP_ERRBUF_SIZE] = {0};
    pcap_t *h = pcap_open_live(iface, snaplen, /*promisc=*/1, /*to_ms=*/200, errbuf);
    if (!h) {
        fprintf(stderr, "pcap_open_live(%s) failed: %s\n", iface, errbuf);
        stats_destroy();
        return 1;
    }

    /* Compile and install the BPF filter; on "any" we pass PCAP_NETMASK_UNKNOWN
     * because that pseudo-device has no single netmask. */
    struct bpf_program fp;
    if (pcap_compile(h, &fp, bpf_expr, /*optimize=*/1, PCAP_NETMASK_UNKNOWN) != 0) {
        fprintf(stderr, "pcap_compile(%s) failed: %s\n", bpf_expr, pcap_geterr(h));
        pcap_close(h); stats_destroy(); return 1;
    }
    if (pcap_setfilter(h, &fp) != 0) {
        fprintf(stderr, "pcap_setfilter failed: %s\n", pcap_geterr(h));
        pcap_freecode(&fp); pcap_close(h); stats_destroy(); return 1;
    }
    pcap_freecode(&fp);

    capture_ctx_t ctx = {
        .iface = iface, .bpf = bpf_expr, .snaplen = snaplen,
        .stop = &g_stop, .handle = h,
    };
    g_capture_ctx = &ctx;

    pthread_t cap_thr;
    if (pthread_create(&cap_thr, NULL, capture_thread_main, &ctx) != 0) {
        fprintf(stderr, "pthread_create failed\n");
        pcap_close(h); stats_destroy(); return 1;
    }

    fprintf(stderr,
        "traffic_monitor " VERSION_STR " up: iface=%s filter=\"%s\" output=%s\n",
        iface, bpf_expr, out_path);

    while (!g_stop) {
        ms_sleep(interval_ms);
        if (g_stop) break;
        stats_tick();
        if (output_write_json(out_path) != 0) {
            perror("output_write_json");
        }
    }

    capture_stop(&ctx);
    pthread_join(cap_thr, NULL);
    pcap_close(h);
    stats_destroy();
    return 0;
}
