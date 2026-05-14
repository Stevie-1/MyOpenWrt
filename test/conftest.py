"""Shared pytest configuration: add backend/ to sys.path so imports work."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


import pytest


@pytest.fixture
def client():
    """Flask test client with MOCK_MODE forced on, ensuring a clean app per test."""
    from app import create_app
    from api import firewall as firewall_module

    firewall_module._mock_rules.clear()
    firewall_module._mock_next_id = 1
    firewall_module._seed_mock_from_file()

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
