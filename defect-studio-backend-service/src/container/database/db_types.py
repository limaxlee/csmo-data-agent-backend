"""Cross-database compatible SQLAlchemy types.

Uses generic types that work on both PostgreSQL and SQLite:
- UUID: Native UUID on PostgreSQL, CHAR(32) on SQLite
- JSONB: Native JSON on both (aliased for code compatibility)
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator, Uuid

JSONB = JSON

class UUID(TypeDecorator):
    impl = Uuid
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        inner = getattr(value, "value", value)
        if isinstance(inner, str):
            inner = uuid.UUID(inner)
        return inner
