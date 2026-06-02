"""Backend runtime configuration.

All settings are read from environment variables with sensible defaults.
This module is imported once by `app.py` and shared across blueprints.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Config:
    version: str = "1.0.0"

    mock_mode: bool = field(default_factory=lambda: _bool_env("MOCK_MODE", True))
    traffic_json_path: str = field(
        default_factory=lambda: os.environ.get("TRAFFIC_JSON_PATH", "/tmp/traffic.json")
    )
    firewall_scripts_dir: str = field(
        default_factory=lambda: os.environ.get("FIREWALL_SCRIPTS_DIR", "/usr/local/bin")
    )
    # Subprocess wall-clock budget for a single firewall script. `fw4 reload`
    # can take a second or two on a busy router, so the default leaves headroom.
    firewall_timeout: float = field(
        default_factory=lambda: float(os.environ.get("FIREWALL_TIMEOUT", "8"))
    )

    flask_host: str = field(default_factory=lambda: os.environ.get("FLASK_HOST", "0.0.0.0"))
    flask_port: int = field(default_factory=lambda: int(os.environ.get("FLASK_PORT", "5000")))

    cors_origins: list[str] = field(
        default_factory=lambda: _list_env(
            "CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )
    )


config = Config()
