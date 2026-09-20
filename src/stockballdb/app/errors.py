"""Application-level errors for the V2 façade."""

from __future__ import annotations


class AppError(Exception):
    """Base error for stockballdb.app use-case failures."""


class AppUnavailableError(AppError):
    """Raised when a required dependency (e.g. the database) is unavailable."""


class AppNotFoundError(AppError):
    """Raised when a requested catalog item does not exist."""
