"""Tests for the REAL (non-mock) firewall path.

On WSL2/CI there is no uci/fw4, so we point FIREWALL_SCRIPTS_DIR at the stub
scripts in test/fixtures/firewall-stub/ (file-backed, no real firewall) and
flip the backend into real mode by monkeypatching api.firewall.config.

This exercises:
- _run_script's argv (shell=False) subprocess wiring
- add -> list -> delete -> clear happy path through actual scripts
- exit-code mapping: del not-found -> 404, script failure -> 500
- missing script -> 500
- defensive ruleId validation -> 422 WITHOUT invoking any script
- validation still fires before subprocess for malicious payloads
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STUB_DIR = REPO_ROOT / "test" / "fixtures" / "firewall-stub"

VALID_RULE = {
    "proto": "tcp",
    "src": "0.0.0.0/0",
    "dst": "192.168.1.1",
    "port": 8080,
    "action": "drop",
}


def _make_real_client(monkeypatch, scripts_dir: Path, state_file: Path):
    """Build a Flask test client whose firewall blueprint runs in real mode
    against `scripts_dir`, with stub state in `state_file`."""
    from app import create_app
    from api import firewall as firewall_module

    real_cfg = dataclasses.replace(
        firewall_module.config,
        mock_mode=False,
        firewall_scripts_dir=str(scripts_dir),
        firewall_timeout=5.0,
    )
    monkeypatch.setattr(firewall_module, "config", real_cfg)
    monkeypatch.setenv("STUB_STATE", str(state_file))

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def real_client(monkeypatch, tmp_path):
    state_file = tmp_path / "state.txt"
    state_file.write_text("", encoding="utf-8")
    return _make_real_client(monkeypatch, STUB_DIR, state_file), state_file


def test_add_list_delete_clear_happy_path(real_client):
    client, _state = real_client

    # initially empty
    assert client.get("/api/firewall/rules").get_json()["rules"] == []

    # add
    resp = client.post("/api/firewall/rules", json=VALID_RULE)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["code"] == 0
    assert body["ruleId"] == "webfw-1"
    assert "Rule webfw-1 added" in body["stdout"]

    # list reflects it, fields round-trip through the script JSON
    rules = client.get("/api/firewall/rules").get_json()["rules"]
    assert len(rules) == 1
    r = rules[0]
    assert r["id"] == "webfw-1"
    assert r["proto"] == "tcp"
    assert r["dst"] == "192.168.1.1"
    assert r["port"] == 8080
    assert r["action"] == "drop"

    # delete
    resp = client.delete("/api/firewall/rules/webfw-1")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert client.get("/api/firewall/rules").get_json()["rules"] == []

    # add two then clear
    client.post("/api/firewall/rules", json=VALID_RULE)
    client.post("/api/firewall/rules", json={**VALID_RULE, "proto": "udp", "port": 53})
    assert len(client.get("/api/firewall/rules").get_json()["rules"]) == 2

    resp = client.post("/api/firewall/clear")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert client.get("/api/firewall/rules").get_json()["rules"] == []


def test_delete_unknown_rule_returns_404(real_client):
    client, _state = real_client
    resp = client.delete("/api/firewall/rules/webfw-999")
    assert resp.status_code == 404
    assert resp.get_json()["ok"] is False


def test_add_runs_script_via_argv_not_shell(real_client):
    """A normal add must persist exactly one line in the stub state file,
    proving the script actually ran (and that we didn't go through mock)."""
    client, state = real_client
    client.post("/api/firewall/rules", json=VALID_RULE)
    lines = [ln for ln in state.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 1
    assert lines[0].startswith("webfw-1|tcp|")


def test_invalid_rule_id_rejected_before_script(monkeypatch, tmp_path):
    """A malformed (but slash-free, route-matching) ruleId must 422 and never
    touch the delete script. We point at a scripts dir whose del_rule.sh would
    'succeed' if called, so a 422 proves we short-circuited."""
    state_file = tmp_path / "state.txt"
    state_file.write_text("webfw-1|tcp|any|any|80|drop\n", encoding="utf-8")
    client = _make_real_client(monkeypatch, STUB_DIR, state_file)

    for bad in ("webfw;1", "..", "a b", "rm$IFS"):
        resp = client.delete(f"/api/firewall/rules/{bad}")
        assert resp.status_code == 422, f"{bad!r} should be rejected"
        assert resp.get_json()["field"] == "ruleId"

    # the pre-existing rule is untouched: no script ran
    assert state_file.read_text(encoding="utf-8") == "webfw-1|tcp|any|any|80|drop\n"


def test_injection_payload_rejected_before_script(real_client):
    client, state = real_client
    payload = {**VALID_RULE, "dst": "1.1.1.1; reboot"}
    resp = client.post("/api/firewall/rules", json=payload)
    assert resp.status_code == 422
    # nothing was added: validation fired before the script
    assert state.read_text(encoding="utf-8") == ""


def test_missing_script_returns_500(monkeypatch, tmp_path):
    empty_dir = tmp_path / "noscripts"
    empty_dir.mkdir()
    state_file = tmp_path / "state.txt"
    client = _make_real_client(monkeypatch, empty_dir, state_file)

    resp = client.post("/api/firewall/rules", json=VALID_RULE)
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["ok"] is False
    assert "not found" in body["message"]


def test_script_nonzero_exit_returns_500(monkeypatch, tmp_path):
    """A script that runs but fails (exit 3) maps to 500 with stdout/stderr
    surfaced verbatim (guide 3.3)."""
    scripts_dir = tmp_path / "failscripts"
    scripts_dir.mkdir()
    add = scripts_dir / "add_rule.sh"
    add.write_text(
        "#!/bin/sh\n"
        "echo 'going to fail'\n"
        "echo 'nft: boom' >&2\n"
        "exit 3\n",
        encoding="utf-8",
    )
    add.chmod(0o755)
    state_file = tmp_path / "state.txt"
    client = _make_real_client(monkeypatch, scripts_dir, state_file)

    resp = client.post("/api/firewall/rules", json=VALID_RULE)
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["ok"] is False
    assert body["code"] == 3
    assert "going to fail" in body["stdout"]
    assert "nft: boom" in body["stderr"]
