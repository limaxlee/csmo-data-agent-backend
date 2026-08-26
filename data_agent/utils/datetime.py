from datetime import datetime, timezone


def convert_unix_to_datetime(timestamp: float, utc: bool = False) -> datetime:
    if utc:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    return datetime.fromtimestamp(timestamp, tz=local_tz)
