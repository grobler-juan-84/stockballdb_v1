"""Service readiness (does not require PostgreSQL)."""

from __future__ import annotations

from fastapi import APIRouter

from stockballdb.api.schemas import ReadyOut

router = APIRouter(tags=["ready"])


@router.get("/ready", response_model=ReadyOut)
def ready() -> ReadyOut:
    """Return HTTP service liveness without checking the database."""
    return ReadyOut(ready=True, service="stockballdb-api")
