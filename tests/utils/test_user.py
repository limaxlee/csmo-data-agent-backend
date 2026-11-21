import pytest

from common.constants import MAX_USER_ID_LENGTH
from data_agent.utils.user import normalize_user_id


class TestNormalizeUserId:
    def test_normalize_user_id(self):
        assert normalize_user_id("user.one") == "user.one"
        assert normalize_user_id("  User.One  ") == "user.one"
        assert normalize_user_id("u" * MAX_USER_ID_LENGTH) == "u" * MAX_USER_ID_LENGTH

    @pytest.mark.parametrize("value", [
        "",
        "   ",
        None,
        7,
        "null",
        "None",
        "UNDEFINED",
        "user one",
        "user\tone",
        "user\x00one",
        "team/user",
        "CORP\\user",
        "u" * (MAX_USER_ID_LENGTH + 1)
    ])
    def test_normalize_user_id_rejects_invalid_values(self, value):
        with pytest.raises(ValueError, match="User id is invalid"):
            normalize_user_id(value)
