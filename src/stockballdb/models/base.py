"""SQLAlchemy declarative base for StockBallDB models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata base for Alembic and ORM models."""
