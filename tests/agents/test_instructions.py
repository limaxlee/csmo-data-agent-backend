from data_agent.agents.instructions import get_instruction_with_current_time


class TestGetInstructionWithCurrentTime:
    def test_returns_provider_with_time_prefix(self, mocker):
        mocker.patch(
            "data_agent.agents.instructions.get_current_local_time",
            return_value="2026-09-02 10:00:00 (Wednesday) UTC+0000"
        )

        provider = get_instruction_with_current_time("Scan the database.")

        assert callable(provider)
        instruction = provider(mocker.MagicMock())
        assert instruction == "CURRENT LOCAL TIME: 2026-09-02 10:00:00 (Wednesday) UTC+0000\n\nScan the database."

    def test_provider_reflects_current_time_on_each_call(self, mocker):
        time_mock = mocker.patch(
            "data_agent.agents.instructions.get_current_local_time",
            side_effect=["first time", "second time"]
        )

        provider = get_instruction_with_current_time("Scan the database.")

        assert provider(mocker.MagicMock()).startswith("CURRENT LOCAL TIME: first time")
        assert provider(mocker.MagicMock()).startswith("CURRENT LOCAL TIME: second time")
        assert time_mock.call_count == 2
