from datetime import datetime, timezone

from common.constants import UserStatus
from data_agent.schemas import UserInfo, UpdateUserResponse

_NOW = datetime(2026, 11, 24, 10, 15, tzinfo=timezone.utc)


def _user(**overrides):
    return {"user_id": "user.one", "is_active": False, "created_at": _NOW, **overrides}


class TestUserInfo:
    def test_status(self):
        assert UserInfo(**_user()).status == UserStatus.WAITING
        assert UserInfo(**_user(is_active=True, activated_at=_NOW)).status == UserStatus.ACTIVE
        assert UserInfo(**_user(activated_at=_NOW, activated_by="admin.one")).status == UserStatus.DEACTIVATED

        # The status is about the approval only: an admin who was never approved still waits.
        assert UserInfo(**_user(is_admin=True)).status == UserStatus.WAITING

        # An account that was approved again after a deactivation is active.
        assert UserInfo(**_user(is_active=True)).status == UserStatus.ACTIVE

        assert UserInfo(**_user()).model_dump()["status"] == "waiting"
        assert UpdateUserResponse(**_user(is_active=True)).model_dump()["status"] == "active"

        # A status that arrives with the data cannot overrule the approval columns.
        assert UserInfo(**_user(status="active")).status == UserStatus.WAITING
