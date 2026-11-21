"""PlanStatus enum."""

from __future__ import annotations

import enum


class PlanStatus(str, enum.Enum):
    """How far a plan has got. A plan only ever moves forward.

    The agent never sends a status — its plan events carry the settings and
    nothing else — so these are inferred from what the run did with the plan.
    """

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    EXECUTED = "executed"

    @property
    def rank(self) -> int:
        """Position in the lifecycle, for comparing two statuses."""
        return _RANK[self]

    @classmethod
    def rank_of(cls, status: str) -> int:
        """Rank of a raw column value; an unrecognised one counts as a draft."""
        try:
            return cls(status).rank
        except ValueError:
            return 0


_RANK = {PlanStatus.DRAFT: 0, PlanStatus.CONFIRMED: 1, PlanStatus.EXECUTED: 2}
