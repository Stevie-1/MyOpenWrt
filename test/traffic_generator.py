"""Simple test traffic generator.

This is a placeholder helper for Phase 2 manual testing. Run it from any
machine that can reach the internet; the C traffic_monitor on OpenWrt will
record the resulting packets. Phase 2 may evolve this into a more focused
benchmarking tool.

Usage:
    python test/traffic_generator.py [count] [interval]
"""

from __future__ import annotations

import socket
import sys
import time


def _udp_burst(target: str, port: int, count: int, interval: float) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        payload = b"x" * 512
        for i in range(count):
            sock.sendto(payload, (target, port))
            if interval > 0:
                time.sleep(interval)
        print(f"sent {count} UDP packets to {target}:{port}")
    finally:
        sock.close()


def main() -> int:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
    _udp_burst("8.8.8.8", 53, count, interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
