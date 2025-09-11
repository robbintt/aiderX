import pytest
from unittest.mock import MagicMock, patch

from unittest.mock import MagicMock, patch

from aider.commands import Commands
from aider.io import InputOutput


class MockCoder:
    def __init__(self):
        self.edit_format = "udiff"
        self.agent = None
        self.handler_manager = None


def test_cmd_pkm_no_args_switches_mode():
    "Test that `/pkm` with no arguments switches to pkm mode"
    mock_coder = MockCoder()
    mock_io = MagicMock(spec=InputOutput)
    agent = MagicMock()
    agent.get_coder.return_value = mock_coder
    commands = Commands(mock_io, agent=agent)

    commands.cmd_pkm("")
    agent.schedule_switch_coder.assert_called_once_with(
        from_coder=mock_coder,
        edit_format="whole",
        handlers=["pkm"],
        summarize_from_coder=False,
    )


@patch("aider.coders.base_coder.Coder.create")
def test_cmd_pkm_with_args_creates_pkm_coder(mock_coder_create):
    "Test that `/pkm` with arguments creates a pkm coder and runs it"
    mock_coder = MockCoder()
    mock_io = MagicMock(spec=InputOutput)
    agent = MagicMock()
    agent.get_coder.return_value = mock_coder
    commands = Commands(mock_io, agent=agent)

    mock_pkm_coder = MagicMock()
    mock_coder_create.return_value = mock_pkm_coder

    commands.cmd_pkm("some pkm request")

    mock_coder_create.assert_called_once_with(
        io=mock_io,
        from_coder=mock_coder,
        edit_format="whole",
        handlers=["pkm"],
        summarize_from_coder=False,
    )

    mock_pkm_coder.run.assert_called_once_with("some pkm request")

    agent.schedule_switch_coder.assert_called_once()
    kwargs = agent.schedule_switch_coder.call_args.kwargs

    assert kwargs["from_coder"] == mock_pkm_coder
    assert kwargs["edit_format"] == "udiff"  # switches back to original coder's edit format
    assert kwargs["handlers"] is None
    assert kwargs["summarize_from_coder"] is False
    assert kwargs["show_announcements"] is False
