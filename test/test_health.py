"""Tests for GET /api/health."""

from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert isinstance(data["ts"], int)
    assert data["ts"] > 0
    assert "mockMode" in data
    assert "version" in data


def test_unknown_path_returns_404(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["ok"] is False
