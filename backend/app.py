"""Flask application entrypoint.

Run locally:
    cd backend && python app.py

Configuration is environment-variable driven (see config.py). Default mode
is MOCK_MODE=true, returning canned JSON from backend/mock/ so the Vue
frontend can be developed independently before the C traffic monitor and
OpenWrt firewall scripts are ready.
"""

from __future__ import annotations

import time

from flask import Flask, jsonify
from flask_cors import CORS

from config import config
from api import firewall_bp, traffic_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    CORS(app, origins=config.cors_origins, supports_credentials=False)

    app.register_blueprint(traffic_bp, url_prefix="/api")
    app.register_blueprint(firewall_bp, url_prefix="/api/firewall")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "ts": int(time.time() * 1000),
                "mockMode": config.mock_mode,
                "version": config.version,
            }
        )

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"ok": False, "message": "not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_err):
        return jsonify({"ok": False, "message": "method not allowed"}), 405

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=config.flask_host, port=config.flask_port, debug=False)
