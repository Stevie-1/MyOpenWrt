"""Firewall configuration API.

Phase 1: returns mock results from an in-memory store, with full strict
validation already wired in via _validators.py. Phase 3 will replace the
mock branches with real subprocess.run() calls to firewall-scripts/*.sh
WITHOUT changing the validation surface or the response shape.

The route prefix /api/firewall is added by app.py.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify, request

from config import config
from ._validators import ValidationError, validate_firewall_payload

logger = logging.getLogger(__name__)

bp = Blueprint("firewall", __name__)

# In-memory mock store. Phase 3 will swap this for real fw4 rule listing.
_store_lock = threading.Lock()
_mock_rules: list[dict[str, Any]] = []
_mock_next_id = 1


def _seed_mock_from_file() -> None:
    """Load initial mock rules from backend/mock/firewall_rules.json once."""
    from pathlib import Path
    import json

    global _mock_next_id
    path = Path(__file__).resolve().parent.parent / "mock" / "firewall_rules.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to load mock firewall rules: %s", exc)
        return

    rules: list[dict[str, Any]] = data.get("rules", []) if isinstance(data, dict) else []
    with _store_lock:
        _mock_rules.clear()
        for rule in rules:
            _mock_rules.append(rule)
        max_n = 0
        for rule in _mock_rules:
            rid = str(rule.get("id", ""))
            if rid.startswith("rule-"):
                try:
                    max_n = max(max_n, int(rid.split("-", 1)[1]))
                except ValueError:
                    pass
        _mock_next_id = max_n + 1


_seed_mock_from_file()


def _ts_payload(extra: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "ts": int(time.time() * 1000), **extra}


def _validation_response(exc: ValidationError):
    payload: dict[str, Any] = {"ok": False, "message": exc.message}
    if exc.field:
        payload["field"] = exc.field
    return jsonify(payload), 422


@bp.get("/rules")
def list_rules():
    with _store_lock:
        rules = list(_mock_rules) if config.mock_mode else _list_real_rules()
    return jsonify({"ok": True, "ts": int(time.time() * 1000), "rules": rules})


@bp.post("/rules")
def add_rule():
    try:
        payload = validate_firewall_payload(request.get_json(silent=True))
    except ValidationError as exc:
        return _validation_response(exc)

    if config.mock_mode:
        global _mock_next_id
        with _store_lock:
            rule_id = f"rule-{_mock_next_id}"
            _mock_next_id += 1
            rule = {"id": rule_id, **asdict(payload)}
            _mock_rules.append(rule)
        return jsonify(
            _ts_payload(
                {
                    "ruleId": rule_id,
                    "stdout": f"Rule {rule_id} added (mock)\n",
                    "stderr": "",
                    "code": 0,
                }
            )
        )

    # Phase 3 will replace this with subprocess.run([...add_rule.sh, ...])
    return _not_implemented("add_rule")


@bp.delete("/rules/<rule_id>")
def delete_rule(rule_id: str):
    if config.mock_mode:
        with _store_lock:
            for i, rule in enumerate(_mock_rules):
                if rule.get("id") == rule_id:
                    _mock_rules.pop(i)
                    return jsonify(
                        _ts_payload(
                            {
                                "stdout": f"Rule {rule_id} deleted (mock)\n",
                                "stderr": "",
                                "code": 0,
                            }
                        )
                    )
        return (
            jsonify({"ok": False, "message": f"rule not found: {rule_id}"}),
            404,
        )

    return _not_implemented("delete_rule")


@bp.post("/clear")
def clear_rules():
    if config.mock_mode:
        with _store_lock:
            count = len(_mock_rules)
            _mock_rules.clear()
        return jsonify(
            _ts_payload(
                {
                    "stdout": f"Cleared {count} rules (mock)\n",
                    "stderr": "",
                    "code": 0,
                }
            )
        )

    return _not_implemented("clear_rules")


def _list_real_rules() -> list[dict[str, Any]]:
    # Phase 3 will implement actual rule listing via list_rules.sh
    logger.warning("real-mode list_rules not implemented; returning empty list")
    return []


def _not_implemented(action: str):
    return (
        jsonify(
            {
                "ok": False,
                "message": f"{action} not yet implemented in non-mock mode (Phase 3)",
                "stdout": "",
                "stderr": "",
                "code": -1,
            }
        ),
        501,
    )
