"""Status HTTP routes — wrap ``stockballdb.app.read.status`` only."""

from __future__ import annotations

from fastapi import APIRouter

from stockballdb.app.read import status as status_app
from stockballdb.api.schemas import ApplicationStatusOut

router = APIRouter(tags=["status"])


@router.get("/status", response_model=ApplicationStatusOut)
def get_status() -> ApplicationStatusOut:
    """
    Return application/database status summary.

    When PostgreSQL is unavailable, P1 returns ``available=False`` without
    raising; this endpoint therefore returns HTTP 200 with that payload so
    clients can render a status screen. Process liveness remains ``GET /ready``.
    """
    return ApplicationStatusOut.from_app(status_app.get_status())
