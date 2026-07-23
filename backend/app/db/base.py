"""Declarative base. All models subclass this so Alembic autogenerate sees one metadata registry."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
