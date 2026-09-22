"""FastAPI application factory for StockBallDB read transport."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockballdb.api.errors import register_exception_handlers
from stockballdb.api.routes import catalog, ready, status
from stockballdb.api.settings import cors_origins


def create_app() -> FastAPI:
    """Build the localhost read-only StockBallDB API."""
    app = FastAPI(
        title="StockBallDB API",
        description="Localhost-only read transport over stockballdb.app (V2).",
        version="0.2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(ready.router)
    app.include_router(catalog.router, prefix="/api/catalog")
    app.include_router(status.router, prefix="/api")
    return app
