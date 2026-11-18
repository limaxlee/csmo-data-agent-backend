"""Entity base class for DDD entities.

All domain entities inherit from this base class. The ``__init_subclass__``
hook automatically applies ``@dataclass(eq=False)`` to every subclass, so
subclasses do **not** need (and should not add) the ``@dataclass`` decorator.

The ``id`` field is generic — subclasses specify the concrete ID type via
``Entity[UserId]``, ``Entity[ThreadId]``, etc.  ID types are typically
:value objects (see :mod:`src.common.domain.value_objects`).

This gives each entity:
- Auto-generated ``__init__`` and ``__repr__`` (from dataclass)
- Identity-based ``__eq__`` — two entities are equal iff their ``id`` matches
- Identity-based ``__hash__`` — consistent with ``__eq__``
- **Runtime type safety** — ``__post_init__`` validates that every field
  declared as a ``BaseID`` subclass actually contains an instance of that
  type, preventing bare ``uuid.UUID`` (from DB reads) or mismatched ID types
  (e.g. ``RunId`` in a ``UserId`` field) from silently flowing in.

Usage::

    class User(Entity[UserId]):
        email: str
        password_hash: str
        # No @dataclass decorator needed!

Subclasses just define their fields as annotated class variables.
"""

from __future__ import annotations

import dataclasses
import typing
import uuid
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, get_args, get_origin

from src.common.domain.value_objects.base_id import BaseID

ID = TypeVar("ID", bound=BaseID)


def _resolve_id_type(declared: Any) -> type[BaseID] | None:
    """Extract the ``BaseID`` subclass from a type annotation, if any.

    Handles plain types (``UserId``) and ``Optional`` / ``Union`` forms
    (``RunId | None``).
    """
    if isinstance(declared, type) and issubclass(declared, BaseID):
        return declared
    origin = get_origin(declared)
    if origin is typing.Union:
        for arg in get_args(declared):
            if isinstance(arg, type) and issubclass(arg, BaseID):
                return arg
    return None


@dataclass(eq=False)
class Entity(Generic[ID]):
    """Base class for all domain entities.

    Entities are distinguished by their identity (``id``), not by their
    attribute values.  Two entities with the same ``id`` are considered
    equal even if their other fields differ.

    The ``id`` type is generic — use ``Entity[YourIdType]`` to specialise.

    The ``__init_subclass__`` hook automatically applies
    ``@dataclass(eq=False)`` to every subclass and captures the concrete
    ID type from the ``Generic`` parameter (e.g. ``Entity[UserId]`` stores
    ``UserId`` in ``cls._id_type``).

    ``__post_init__`` validates that every field whose declared type is a
    ``BaseID`` subclass actually contains an instance of that subclass at
    runtime.  This catches:

    - Bare ``uuid.UUID`` flowing in from DB reads (the original issue #93).
    - Mismatched ID types (e.g. ``RunId`` where ``UserId`` is expected).

    Subclasses should NOT add ``@dataclass`` — it is handled automatically.
    """

    id: ID

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Extract the concrete ID type from the Generic parameter, e.g.
        # class User(Entity[UserId]) → cls._id_type = UserId
        for base in getattr(cls, "__orig_bases__", ()):
            origin = get_origin(base)
            if isinstance(origin, type) and issubclass(origin, Entity):
                args = get_args(base)
                if args and isinstance(args[0], type):
                    cls._id_type: type[BaseID] = args[0]
                    break
        dataclass(eq=False)(cls)

    def __post_init__(self) -> None:
        """Validate and coerce ID-typed fields.

        - ``None`` → left as-is (optional fields).
        - Already the correct ``BaseID`` subclass → left as-is.
        - Bare ``uuid.UUID`` → auto-wrapped into the expected ``BaseID``
          subclass (convenience for ``create()`` and tests).
        - Wrong ``BaseID`` subclass (e.g. ``RunId`` where ``UserId`` is
          expected) → ``TypeError`` raised immediately.
        """
        cls = type(self)
        # Build and cache the field→expected-type map once per class
        if "_id_field_map" not in cls.__dict__:
            field_map: dict[str, type[BaseID]] = {}
            try:
                hints = typing.get_type_hints(cls)
            except Exception:
                hints = {}
            field_names = {f.name for f in dataclasses.fields(cls)}
            id_type = getattr(cls, "_id_type", None)
            for name in field_names:
                if name not in hints:
                    continue
                resolved = _resolve_id_type(hints[name])
                # The inherited ``id`` field is annotated as the TypeVar ``ID``,
                # which get_type_hints cannot resolve to a concrete class —
                # fall back to the ``_id_type`` captured in __init_subclass__.
                if resolved is None and name == "id" and id_type:
                    resolved = id_type
                if resolved:
                    field_map[name] = resolved
            cls._id_field_map = field_map  # type: ignore[attr-defined]

        for name, expected in cls._id_field_map.items():  # type: ignore[attr-defined]
            val = getattr(self, name)
            if val is None:
                continue
            if isinstance(val, expected):
                continue
            # Wrong BaseID subclass — this is the type-safety error we catch
            if isinstance(val, BaseID):
                raise TypeError(
                    f"{cls.__name__}.{name} must be {expected.__name__}, "
                    f"got {type(val).__name__}"
                )
            # Bare uuid.UUID → auto-wrap for convenience
            if isinstance(val, uuid.UUID):
                object.__setattr__(self, name, expected(val))
                continue
            # Anything else is a type error
            raise TypeError(
                f"{cls.__name__}.{name} must be {expected.__name__}, "
                f"got {type(val).__name__}"
            )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        if type(self) is not type(other):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))
