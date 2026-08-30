from datetime import timezone

from data_agent.utils import convert_unix_to_datetime


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
