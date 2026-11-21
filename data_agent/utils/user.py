from common.constants import MAX_USER_ID_LENGTH

_RESERVED_USER_IDS = {"undefined", "null", "none"}
_FORBIDDEN_USER_ID_CHARS = {"/", "\\"}


def normalize_user_id(value: str) -> str:
    user_id = value.strip().casefold() if isinstance(value, str) else ""

    if not user_id or len(user_id) > MAX_USER_ID_LENGTH or user_id in _RESERVED_USER_IDS:
        raise ValueError("User id is invalid")

    if any(char.isspace() or ord(char) < 32 or char in _FORBIDDEN_USER_ID_CHARS for char in user_id):
        raise ValueError("User id is invalid")

    return user_id
