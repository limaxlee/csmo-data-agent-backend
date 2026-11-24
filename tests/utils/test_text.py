from data_agent.utils.text import normalize_text_filter


class TestNormalizeTextFilter:
    def test_normalize_text_filter(self):
        assert normalize_text_filter("hong") == "hong"
        assert normalize_text_filter("  Gil Dong  ") == "Gil Dong"

        for value in [None, "", "   ", "\t\n", 7]:
            assert normalize_text_filter(value) is None
