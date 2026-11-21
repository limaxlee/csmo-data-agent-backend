"""ThreadStatus enum."""

from __future__ import annotations

import enum


class ThreadStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
