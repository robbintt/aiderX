import pytest
from unittest.mock import MagicMock, patch

from aider.commands import Commands, SwitchCoder
from aider.io import InputOutput


class MockCoder:
    def __init__(self):
        self.edit_format = "udiff"
        self.pkm_mode = False


def test_cmd_pkm_no_args_switches_mode():
    "Test that `/pkm` with no arguments switches to pkm mode"
    mock_coder = MockCoder()
    mock_io = MagicMock(spec=InputOutput)
    commands = Commands(mock_io, mock_coder)

    res = commands.cmd_pkm("")
    assert isinstance(res, SwitchCoder)

    assert res.pkm_mode is True
    assert res.edit_format == "diff-fenced"
    assert res.from_coder == mock_coder
    assert res.summarize_from_coder is False
    assert res.show_announcements is True  # default


@patch("aider.coders.base_coder.Coder.create")
def test_cmd_pkm_with_args_creates_pkm_coder(mock_coder_create):
    "Test that `/pkm` with arguments creates a pkm coder and runs it"
    mock_coder = MockCoder()
    mock_io = MagicMock(spec=InputOutput)
    commands = Commands(mock_io, mock_coder)

    mock_pkm_coder = MagicMock()
    mock_coder_create.return_value = mock_pkm_coder

    res = commands.cmd_pkm("some pkm request")
    assert isinstance(res, SwitchCoder)

    mock_coder_create.assert_called_once_with(
        io=mock_io,
        from_coder=mock_coder,
        edit_format="diff-fenced",
        pkm_mode=True,
        summarize_from_coder=False,
    )

    mock_pkm_coder.run.assert_called_once_with("some pkm request")

    assert res.from_coder == mock_pkm_coder
    assert res.edit_format == "udiff"  # switches back to original coder's edit format
    assert res.pkm_mode is False
    assert res.summarize_from_coder is False
    assert res.show_announcements is False
    assert res.placeholder is None
