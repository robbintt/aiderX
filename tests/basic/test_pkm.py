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
    commands = Commands(mock_io, mock_coder, agent=agent)

    commands.cmd_pkm("")
    agent.schedule_switch_coder.assert_called_once()

    assert excinfo.value.handlers == ["pkm"]
    assert excinfo.value.edit_format == "whole"
    assert excinfo.value.from_coder == mock_coder
    assert excinfo.value.summarize_from_coder is False


@patch("aider.coders.base_coder.Coder.create")
def test_cmd_pkm_with_args_creates_pkm_coder(mock_coder_create):
    "Test that `/pkm` with arguments creates a pkm coder and runs it"
    mock_coder = MockCoder()
    mock_io = MagicMock(spec=InputOutput)
    agent = MagicMock()
    mock_coder.agent = agent
    commands = Commands(mock_io, mock_coder, agent=agent)

    mock_pkm_coder = MagicMock()
    mock_coder_create.return_value = mock_pkm_coder

    commands.cmd_pkm("some pkm request")
    agent.schedule_switch_coder.assert_called_once()
    kwargs = agent.schedule_switch_coder.call_args.kwargs

    mock_coder_create.assert_called_once_with(
        io=mock_io,
        from_coder=mock_coder,
        edit_format="whole",
        handlers=["pkm"],
        summarize_from_coder=False,
    )

    mock_pkm_coder.run.assert_called_once_with("some pkm request")

    assert excinfo.value.from_coder == mock_pkm_coder
    assert excinfo.value.edit_format == "udiff"  # switches back to original coder's edit format
    assert excinfo.value.handlers is None
    assert excinfo.value.summarize_from_coder is False
    assert excinfo.value.show_announcements is False
