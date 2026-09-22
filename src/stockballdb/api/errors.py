"""Map ``stockballdb.app`` errors to structured HTTP responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from stockballdb.app.errors import AppError, AppNotFoundError, AppUnavailableError
from stockballdb.api.schemas import ErrorBody, ErrorResponse

logger = logging.getLogger("stockballdb.api")


def _error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or {})
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppNotFoundError)
    async def not_found_handler(_request: Request, exc: AppNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error_payload("not_found", str(exc)),
        )

    @app.exception_handler(AppUnavailableError)
    async def unavailable_handler(_request: Request, exc: AppUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=_error_payload("unavailable", str(exc)),
        )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_error_payload("app_error", str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "validation_error",
                "request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled API error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                "internal_error",
                "an unexpected error occurred",
            ),
        )
