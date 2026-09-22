"""Localhost-only FastAPI transport over ``stockballdb.app`` (V2 P2).

This package is HTTP-specific. Application logic stays in ``stockballdb.app``.
"""

from stockballdb.api.app import create_app

__all__ = ["create_app"]
