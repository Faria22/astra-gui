"""Tests for popup helpers that wrap tkinter messagebox/filedialog."""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import DialogSpy

try:
    from astra_gui.utils import popup_module
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils import popup_module


@pytest.fixture
def popup_spy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> DialogSpy:
    """Patch popup_module messagebox helpers with a local spy.

    Returns
    -------
    DialogSpy
        Spy instance capturing popup interactions.
    """
    spy = DialogSpy(tmp_path)
    monkeypatch.setattr(popup_module, 'messagebox', spy)
    monkeypatch.setattr(popup_module, 'filedialog', spy, raising=False)
    return spy


def test_idle_processor_popup_uses_yesno(popup_spy: DialogSpy) -> None:
    """Prompt should ask for confirmation and respect the return value."""
    popup_spy.set_response('askyesno', True)
    assert popup_module.idle_processor_popup('cpu-0', 80) is True
    last_call = popup_spy.calls[-1]
    assert last_call.method == 'askyesno'
    assert 'cpu-0' in last_call.args[1]


@pytest.mark.parametrize(
    ('func', 'message', 'requires_arg'),
    [
        (popup_module.missing_required_calculation_popup, 'Missing Required Calculation', True),
        (popup_module.not_gui_pulse_file_popup, 'Not a pulse file', False),
        (popup_module.required_field_popup, 'Required field', True),
        (popup_module.directory_popup, 'No directory selected', False),
        (popup_module.completed_calculation_popup, 'Completed Calculation', True),
        (popup_module.missing_script_file_popup, 'Missing script file', True),
        (popup_module.help_popup, 'Help', False),
        (popup_module.about_popup, 'About', False),
        (popup_module.missing_output_popup, 'Missing output', True),
        (popup_module.missing_required_file_popup, 'Required file missing', True),
        (popup_module.invalid_input_popup, 'Invalid Input', True),
        (popup_module.warning_popup, 'Warning', True),
    ],
)
def test_messagebox_wrappers_forward_to_spy(
    popup_spy: DialogSpy,
    func: Callable[..., Any],
    message: str,
    requires_arg: bool,
) -> None:
    """Every popup helper should forward to the appropriate messagebox API."""
    if requires_arg:
        func('example')
    else:
        func()
    assert popup_spy.calls, 'Expected a dialog call to be recorded'
    last_call = popup_spy.calls[-1]
    assert message.lower().split()[0] in last_call.args[0].lower()


def test_create_path_popup_returns_configured_response(popup_spy: DialogSpy) -> None:
    """Create-path prompt should use askyesno and report the response."""
    popup_spy.set_response('askyesno', True)
    result = popup_module.create_path_popup('/tmp/missing')
    assert result is True
    last_call = popup_spy.calls[-1]
    assert last_call.method == 'askyesno'
    assert '/tmp/missing' in last_call.args[1]


def test_calculation_is_running_popup_uses_yesno(popup_spy: DialogSpy) -> None:
    """Calculation-in-progress prompt should ask for confirmation."""
    popup_module.calculation_is_running_popup('astra')
    last_call = popup_spy.calls[-1]
    assert last_call.method == 'askyesno'
    assert 'astra' in last_call.args[1]


def test_overwrite_warning_popup_default_false(popup_spy: DialogSpy) -> None:
    """Overwrite warning should default to False when spy has no override."""
    assert popup_module.overwrite_warning_popup() is False
    assert popup_spy.calls[-1].method == 'askyesno'
