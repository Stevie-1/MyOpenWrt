"""Validate the JSON written by traffic_monitor against docs/api.md.

Strategy:
  1. Always validate backend/mock/traffic.json (must stay schema-valid).
  2. If the host build of traffic_monitor exists, invoke it with
     `--self-test` to write a fresh JSON to a tmp path and validate that
     output too. This exercises the production C path (stats + output.c)
     without needing CAP_NET_RAW.
"""

from __future__ import annotations

import ipaddress
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MOCK_PATH = REPO_ROOT / "backend" / "mock" / "traffic.json"
HOST_BIN = REPO_ROOT / "traffic-monitor" / "bin" / "traffic_monitor"

REQUIRED_FIELDS = {
    "srcIp": str,
    "dstIp": str,
    "srcPort": int,
    "dstPort": int,
    "proto": str,
    "rxBytes": int,
    "txBytes": int,
    "peak": int,
    "avg2s": int,
    "avg10s": int,
    "avg40s": int,
}
ALLOWED_PROTOS = {"tcp", "udp", "icmp", "other"}


def _validate_envelope(doc: dict) -> list:
    assert isinstance(doc, dict), f"top-level must be object, got {type(doc).__name__}"
    assert "items" in doc, "missing top-level 'items'"
    items = doc["items"]
    assert isinstance(items, list), "'items' must be a list"
    # ts is required for the live file (mock JSON may omit it; backend
    # injects its own server-side ts). When present, ensure it's an int.
    if "ts" in doc:
        assert isinstance(doc["ts"], int) and doc["ts"] >= 0, "ts must be non-negative int"
    return items


def _validate_item(item: dict) -> None:
    for field, ty in REQUIRED_FIELDS.items():
        assert field in item, f"item missing field: {field}"
        assert isinstance(item[field], ty), (
            f"{field} must be {ty.__name__}, got {type(item[field]).__name__}"
        )
    ipaddress.IPv4Address(item["srcIp"])
    ipaddress.IPv4Address(item["dstIp"])
    assert 0 <= item["srcPort"] <= 65535, "srcPort out of range"
    assert 0 <= item["dstPort"] <= 65535, "dstPort out of range"
    assert item["proto"] in ALLOWED_PROTOS, f"proto '{item['proto']}' not in {ALLOWED_PROTOS}"
    for k in ("rxBytes", "txBytes", "peak", "avg2s", "avg10s", "avg40s"):
        assert item[k] >= 0, f"{k} must be non-negative"


def test_mock_traffic_schema():
    doc = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
    items = _validate_envelope(doc)
    assert items, "mock items should not be empty (used by frontend dev)"
    for it in items:
        _validate_item(it)


@pytest.mark.skipif(not HOST_BIN.exists(), reason="host build not present; run `make` in traffic-monitor/")
def test_self_test_output_schema(tmp_path):
    out = tmp_path / "traffic.json"
    res = subprocess.run(
        [str(HOST_BIN), "--self-test", "-o", str(out)],
        capture_output=True, text=True, timeout=10,
    )
    assert res.returncode == 0, f"self-test failed: {res.stderr}"
    assert out.exists(), "self-test did not produce output file"
    doc = json.loads(out.read_text(encoding="utf-8"))
    items = _validate_envelope(doc)
    assert len(items) >= 1, "self-test should inject synthetic flows"
    for it in items:
        _validate_item(it)
    # Sanity: at least one TCP item with non-zero counters comes from the
    # injected k1 (192.168.1.10 -> 8.8.8.8:443).
    assert any(
        it["proto"] == "tcp" and it["rxBytes"] > 0 and it["txBytes"] > 0
        for it in items
    ), "expected at least one TCP item with rx+tx > 0"
