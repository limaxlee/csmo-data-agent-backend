import re
from datetime import datetime, timezone

from data_agent.utils import convert_unix_to_datetime, get_current_local_time


class TestDatetimeUtils:
    def test_convert_unix_to_datetime(self):
        timestamp = 1700000000.0

        utc_result = convert_unix_to_datetime(timestamp, utc=True)
        assert utc_result.tzinfo is timezone.utc
        assert utc_result.timestamp() == timestamp

        local_result = convert_unix_to_datetime(timestamp)
        assert local_result.tzinfo is not None
        assert local_result.timestamp() == timestamp

        assert local_result == utc_result

    def test_get_current_local_time(self):
        result = get_current_local_time()

        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \((\w+)\) .*", result)
        assert match is not None

        parsed = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        assert abs((datetime.now() - parsed).total_seconds()) < 60
        assert match.group(2) == parsed.strftime("%A")
