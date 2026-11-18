"""The one place timestamps are minted.

Every timestamp column in this codebase is ``DateTime(timezone=True)``
(Postgres ``timestamptz``). A naive value handed to such a column is read by
Postgres in the *session* time zone, so ``datetime.utcnow()`` only stored the
right instant as long as the server happened to be set to UTC — an unwritten
dependency that would shift every timestamp on a differently configured
instance. ``utc_now()`` is explicit instead, and it is not deprecated the way
``utcnow()`` is on 3.12.

Note what this does *not* fix. SQLite has no time-zone type and silently drops
tzinfo, so the SQLite used in tests still reads these values back naive while
Postgres returns them aware. Any arithmetic on a timestamp read from the
database therefore still has to normalise first, or it raises
"can't subtract offset-naive and offset-aware datetimes" in exactly one of the
two environments. Do not remove such normalisation on the grounds that writes
are aware now.

Two kinds of call site deliberately still use ``datetime.utcnow()``, because
their output is a string rather than a stored instant:

- ``train_data`` handlers writing ``last_updated`` into ``metadata.json``
  (``upload_train_data_handler``, ``delete_train_data_file_handler``,
  ``delete_all_train_data_handler``). DefectAgent reads that file, and an aware
  value would append "+00:00" and change the format.
- ``upload_train_data_handler``'s ``strftime("%Y%m%d%H%M%S%f")`` storage-key
  prefixes, where tzinfo makes no difference to the result.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """The current instant, as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

