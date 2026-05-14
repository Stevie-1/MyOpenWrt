"""API blueprints package."""

from .traffic import bp as traffic_bp
from .firewall import bp as firewall_bp

__all__ = ["traffic_bp", "firewall_bp"]
