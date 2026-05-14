"""Traffic monitoring API.

In mock mode (MOCK_MODE=true) it serves backend/mock/traffic.json directly.
In real mode it reads TRAFFIC_JSON_PATH (default /tmp/traffic.json) which
is written by the C/libpcap traffic monitor every second.

Either way the response shape matches docs/api.md so the frontend works
identically against both modes.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify

from config import config

logger = logging.getLogger(__name__)

bp = Blueprint("traffic", __name__)

_MOCK_PATH = Path(__file__).resolve().parent.parent / "mock" / "traffic.json"


def _load_mock_items() -> list[dict]:
    try:
        with _MOCK_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to read mock traffic data: %s", exc)
        return []
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    return []


def _load_live_items() -> list[dict]:
    path = config.traffic_json_path
    if not os.path.exists(path):
        logger.warning("live traffic file not found: %s; returning empty items", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to read live traffic file %s: %s", path, exc)
        return []
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    return []


@bp.get("/traffic")
def get_traffic():
    items = _load_mock_items() if config.mock_mode else _load_live_items()
    return jsonify(
        {
            "ok": True,
            "ts": int(time.time() * 1000),
            "items": items,
        }
    )
