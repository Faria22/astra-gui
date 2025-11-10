"""Tests for the status bar widget that queues messages."""

import sys
import types
from collections import deque
from pathlib import Path
from typing import Any

try:
    from astra_gui.utils.statusbar_module import StatusBar
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils.statusbar_module import StatusBar


class DummyRoot:
    """Minimal Tk-like root capturing scheduled callbacks."""

    def __init__(self) -> None:
        self.callbacks: list[tuple[Any, tuple[Any, ...]]] = []

    def after(self, _delay: int, callback: Any | None = None, *args: Any) -> str:
        """Store callbacks to be executed later.

        Returns
        -------
        str
            Token identifying the queued callback.
        """
        if callback is not None:
            self.callbacks.append((callback, args))
        return f'after#{len(self.callbacks)}'

    def run_after(self, count: int | None = None) -> None:
        """Execute queued callbacks respecting the provided limit."""
        executed = 0
        while self.callbacks and (count is None or executed < count):
            callback, args = self.callbacks.pop(0)
            callback(*args)
            executed += 1


def make_status_bar(default: str = 'Ready') -> tuple[StatusBar, DummyRoot]:
    """Return a StatusBar instance backed by dummy Tk primitives.

    Returns
    -------
    tuple[StatusBar, DummyRoot]
        Status bar under test plus its owning dummy root.
    """
    root = DummyRoot()
    status = StatusBar.__new__(StatusBar)
    status.root = root  # type: ignore[attr-defined]
    status.default_message = default  # type: ignore[attr-defined]
    status.message_queue = deque()  # type: ignore[attr-defined]
    status.is_displaying_message = False  # type: ignore[attr-defined]
    status.status_text = default  # type: ignore[attr-defined]

    status.config = types.MethodType(statusbar_config, status)  # type: ignore[assignment]
    status.cget = types.MethodType(statusbar_cget, status)  # type: ignore[assignment]
    return status, root


def statusbar_config(self: StatusBar, **kwargs: Any) -> None:
    """Update the stored text when configuring the widget."""
    if 'text' in kwargs:
        self.status_text = kwargs['text']  # type: ignore[attr-defined]


def statusbar_cget(self: StatusBar, key: str) -> Any:
    """Return the stored configuration value for the requested key.

    Returns
    -------
    Any
        Stored value for the requested option when available.
    """
    if key == 'text':
        return self.status_text  # type: ignore[attr-defined]
    raise KeyError(key)


def test_show_message_updates_label_and_resets() -> None:
    """Queued message should display immediately and reset after callback."""
    status, root = make_status_bar()

    status.show_message('Processing', time=0)

    assert status.cget('text') == 'Processing'
    assert status.is_displaying_message is True

    root.run_after(count=1)

    assert status.cget('text') == 'Ready'
    assert status.is_displaying_message is False


def test_overwrite_default_text_persists_value() -> None:
    """Overwriting the default text should persist after queue drains."""
    status, root = make_status_bar('Initial')

    status.show_message('New Default', overwrite_default_text=True)
    root.run_after(count=1)

    assert status.default_message == 'New Default'
    assert status.cget('text') == 'New Default'


def test_message_queue_processes_last_in_first_out() -> None:
    """Queued messages should be processed in arrival order."""
    status, root = make_status_bar('Idle')

    status.show_message('first')
    status.show_message('second')
    status.show_message('third')

    assert status.cget('text') == 'first'
    assert list(status.message_queue) == [('second', 0), ('third', 0)]

    root.run_after(count=1)
    assert status.cget('text') == 'second'
    assert list(status.message_queue) == [('third', 0)]

    root.run_after(count=1)
    assert status.cget('text') == 'third'
    assert list(status.message_queue) == []

    root.run_after(count=1)
    assert status.cget('text') == 'Idle'
    assert status.is_displaying_message is False
