"""Firewall configuration API.

Two execution modes, selected by config.mock_mode:

- Mock (MOCK_MODE=true, default): an in-memory store backs add/list/delete/
  clear so the Vue frontend can be built without OpenWrt.
- Real (MOCK_MODE=false): each endpoint shells out to firewall-scripts/*.sh
  via subprocess.run([...], shell=False). The scripts manage uci/fw4 rules on
  OpenWrt. stdout/stderr/exit-code are surfaced verbatim (guide section 3.3).

Both modes share the same strict validation (_validators.py) and the same
response shape (docs/api.md), so the frontend is agnostic to the mode.

The route prefix /api/firewall is added by app.py.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify, request

from config import config
from ._validators import (
    ValidationError,
    validate_firewall_payload,
    validate_rule_id,
)

logger = logging.getLogger(__name__)

bp = Blueprint("firewall", __name__)


class ScriptError(RuntimeError):
    """Raised when a firewall script cannot be executed at all (missing,
    not executable, or timed out). Distinct from a script that runs and
    returns a non-zero exit code."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _run_script(name: str, args: list[str]) -> tuple[int, str, str]:
    """Execute a firewall script with argv passing (never shell=True).

    Returns (returncode, stdout, stderr). Raises ScriptError if the script
    is missing/not executable or exceeds the timeout budget.
    """
    path = os.path.join(config.firewall_scripts_dir, name)
    try:
        proc = subprocess.run(
            [path, *args],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=config.firewall_timeout,
        )
    except FileNotFoundError as exc:
        raise ScriptError(f"firewall script not found: {path}") from exc
    except PermissionError as exc:
        raise ScriptError(f"firewall script not executable: {path}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ScriptError(f"firewall script timeout: {name}") from exc
    return proc.returncode, proc.stdout, proc.stderr


def _script_error_response(exc: ScriptError):
    return (
        jsonify(
            {
                "ok": False,
                "message": exc.message,
                "stdout": "",
                "stderr": "",
                "code": -1,
            }
        ),
        500,
    )


def _script_failed_response(stdout: str, stderr: str, code: int):
    return (
        jsonify(
            {
                "ok": False,
                "message": "firewall script failed",
                "stdout": stdout,
                "stderr": stderr,
                "code": code,
            }
        ),
        500,
    )


def _parse_rule_id(stdout: str) -> str | None:
    """add_rule.sh prints a `ruleId=<id>` line on success."""
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("ruleId="):
            return line.split("=", 1)[1].strip()
    return None

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
    if config.mock_mode:
        with _store_lock:
            rules = list(_mock_rules)
        return jsonify({"ok": True, "ts": int(time.time() * 1000), "rules": rules})

    try:
        rules = _list_real_rules()
    except ScriptError as exc:
        return _script_error_response(exc)
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

    try:
        code, stdout, stderr = _run_script(
            "add_rule.sh",
            [payload.proto, payload.src, payload.dst, str(payload.port), payload.action],
        )
    except ScriptError as exc:
        return _script_error_response(exc)

    if code != 0:
        return _script_failed_response(stdout, stderr, code)

    return jsonify(
        _ts_payload(
            {
                "ruleId": _parse_rule_id(stdout),
                "stdout": stdout,
                "stderr": stderr,
                "code": code,
            }
        )
    )


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

    try:
        rule_id = validate_rule_id(rule_id)
    except ValidationError as exc:
        return _validation_response(exc)

    try:
        code, stdout, stderr = _run_script("del_rule.sh", [rule_id])
    except ScriptError as exc:
        return _script_error_response(exc)

    # del_rule.sh contract: 0=deleted, 1=not found, other=failure.
    if code == 1:
        return (
            jsonify({"ok": False, "message": f"rule not found: {rule_id}"}),
            404,
        )
    if code != 0:
        return _script_failed_response(stdout, stderr, code)

    return jsonify(_ts_payload({"stdout": stdout, "stderr": stderr, "code": code}))


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

    try:
        code, stdout, stderr = _run_script("clear_rules.sh", [])
    except ScriptError as exc:
        return _script_error_response(exc)

    if code != 0:
        return _script_failed_response(stdout, stderr, code)

    return jsonify(_ts_payload({"stdout": stdout, "stderr": stderr, "code": code}))


def _list_real_rules() -> list[dict[str, Any]]:
    """Invoke list_rules.sh and parse its JSON stdout.

    A malformed payload is logged and degraded to an empty list rather than
    bubbling a 500, so a transient parse glitch doesn't take down the page.
    """
    code, stdout, stderr = _run_script("list_rules.sh", [])
    if code != 0:
        logger.warning("list_rules.sh exited %d: %s", code, stderr.strip())
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.warning("list_rules.sh produced invalid JSON: %s", exc)
        return []
    if isinstance(data, dict) and isinstance(data.get("rules"), list):
        return data["rules"]
    logger.warning("list_rules.sh JSON missing 'rules' array")
    return []
