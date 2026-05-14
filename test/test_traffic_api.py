"""Tests for GET /api/traffic in MOCK_MODE."""

from __future__ import annotations

REQUIRED_KEYS = {
    "srcIp", "dstIp", "srcPort", "dstPort", "proto",
    "rxBytes", "txBytes", "peak", "avg2s", "avg10s", "avg40s",
}

ALLOWED_PROTO = {"tcp", "udp", "icmp", "other"}


def test_traffic_returns_ok_with_items(client):
    resp = client.get("/api/traffic")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert isinstance(data["ts"], int)
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_traffic_item_fields_match_contract(client):
    resp = client.get("/api/traffic")
    data = resp.get_json()
    for item in data["items"]:
        missing = REQUIRED_KEYS - set(item.keys())
        assert not missing, f"missing keys in traffic item: {missing}"
        assert item["proto"] in ALLOWED_PROTO
        assert isinstance(item["srcPort"], int)
        assert isinstance(item["dstPort"], int)
        assert 0 <= item["srcPort"] <= 65535
        assert 0 <= item["dstPort"] <= 65535
        for numeric in ("rxBytes", "txBytes", "peak", "avg2s", "avg10s", "avg40s"):
            assert isinstance(item[numeric], int)
            assert item[numeric] >= 0
