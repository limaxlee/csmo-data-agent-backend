"""Base identifier value object.

All identifier value objects (both shared and context-local) inherit from
``BaseID`` to get value-based equality, hashing, and a ``generate()``
factory for free.

Using typed ID objects instead of bare ``uuid.UUID`` / ``str`` prevents
mixing up IDs at the type-checker level (e.g. passing a ``UserId`` where a
``ThreadId`` is expected).  ``__eq__`` also accepts bare ``uuid.UUID`` for
ergonomic comparisons in tests (``UserId(uuid) == uuid`` is ``True``),
while still distinguishing between different ID types (``UserId != RunId``
even if they hold the same UUID).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class BaseID:
    """Base class for all identifier value objects.

    Subclasses are expected to be simple specialisations with no additional
    fields — they exist purely so the type system can distinguish one ID
    kind from another::

        @dataclass(frozen=True, eq=False)
        class UserId(BaseID):
            pass

    ``__eq__`` compares by type *and* value, so two IDs of different types
    are never equal even if they wrap the same UUID.  Comparison with a
    bare ``uuid.UUID`` is also supported (returns ``True`` when the inner
    UUID matches) for ergonomic testing.
    """

    value: uuid.UUID

    @classmethod
    def generate(cls) -> BaseID:
        """Create a new ID with a randomly generated UUID."""
        return cls(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseID):
            return type(self) is type(other) and self.value == other.value
        if isinstance(other, uuid.UUID):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return str(self.value)
    