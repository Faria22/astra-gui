"""Shared pytest fixtures for ASTRA GUI tests."""

import io
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import partialmethod
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Self

import pytest

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:  # pragma: no cover - handled in fixtures
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from tkinter import Tk as TkWidget
else:
    TkWidget = Any  # type: ignore[assignment]

try:
    import paramiko
except ImportError:  # pragma: no cover - optional dependency for tests
    paramiko = None  # type: ignore[assignment]


# --- Tkinter fixtures -----------------------------------------------------


@pytest.fixture
def tk_root() -> Iterator[TkWidget]:
    """Return a withdrawn Tk root with captured tkinter `after` callbacks.

    Yields
    ------
    Tk
        Root widget where `after` callbacks can be driven deterministically.
    """
    if tk is None:
        pytest.skip('tkinter is not available in this environment')

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # type: ignore[attr-defined]
        pytest.skip(f'tkinter backend unavailable: {exc}')

    root.withdraw()

    root.astra_scheduled_callbacks = []  # type: ignore[attr-defined]
    root.after = types.MethodType(_tk_after, root)  # type: ignore[assignment]
    root.run_after_callbacks = types.MethodType(_tk_run_after_callbacks, root)  # type: ignore[attr-defined]
    yield root
    root.destroy()


# --- Dialog patching helpers ----------------------------------------------


@dataclass(slots=True)
class DialogCall:
    """Record of a dialog invocation."""

    method: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    response: Any


@dataclass(slots=True)
class DialogSpy:
    """Spy object for tkinter messagebox and filedialog interactions."""

    tmp_path: Path
    default_directory: Path = field(init=False)
    calls: list[DialogCall] = field(default_factory=list)
    _responses: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Create a default directory for dialog responses."""
        self.default_directory = self.tmp_path / 'dialog'
        self.default_directory.mkdir(parents=True, exist_ok=True)

    def set_response(self, method: str, value: Any) -> None:
        """Override the default return value for a dialog method."""
        self._responses[method] = value

    def _record(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Capture a dialog call and return the configured response.

        Returns
        -------
        Any
            The stubbed response associated with the dialog method.
        """
        response = self._responses.get(method)
        if response is None:
            if method in {'askyesno', 'askokcancel', 'askyesnocancel'}:
                response = False
            elif method == 'askdirectory':
                response = str(self.default_directory)
            elif method in {'asksaveasfilename', 'askopenfilename'}:
                response = str(self.default_directory / 'selected.txt')
            else:
                response = None
        self.calls.append(DialogCall(method, args, kwargs, response))
        return response

    # Messagebox methods --------------------------------------------------
    showinfo: ClassVar[Any] = partialmethod(_record, 'showinfo')
    showwarning: ClassVar[Any] = partialmethod(_record, 'showwarning')
    showerror: ClassVar[Any] = partialmethod(_record, 'showerror')
    askyesno: ClassVar[Any] = partialmethod(_record, 'askyesno')
    askokcancel: ClassVar[Any] = partialmethod(_record, 'askokcancel')

    # Filedialog methods --------------------------------------------------
    askdirectory: ClassVar[Any] = partialmethod(_record, 'askdirectory')
    askopenfilename: ClassVar[Any] = partialmethod(_record, 'askopenfilename')
    asksaveasfilename: ClassVar[Any] = partialmethod(_record, 'asksaveasfilename')


@pytest.fixture
def dialog_spy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> DialogSpy:
    """Patch tkinter dialogs with a spy that records invocations.

    Returns
    -------
    DialogSpy
        Spy instance capturing messagebox and filedialog calls.
    """
    spy = DialogSpy(tmp_path)

    if tk is None or messagebox is None or filedialog is None:
        pytest.skip('tkinter is not available in this environment')

    monkeypatch.setattr(messagebox, 'showinfo', spy.showinfo)
    monkeypatch.setattr(messagebox, 'showwarning', spy.showwarning)
    monkeypatch.setattr(messagebox, 'showerror', spy.showerror)
    monkeypatch.setattr(messagebox, 'askyesno', spy.askyesno)
    monkeypatch.setattr(messagebox, 'askokcancel', spy.askokcancel)

    monkeypatch.setattr(filedialog, 'askdirectory', spy.askdirectory)
    monkeypatch.setattr(filedialog, 'askopenfilename', spy.askopenfilename)
    monkeypatch.setattr(filedialog, 'asksaveasfilename', spy.asksaveasfilename)

    return spy


# --- Paramiko fakes --------------------------------------------------------


class _FakeChannel:
    """Lightweight channel stub exposing exit status."""

    def __init__(self, exit_status: int) -> None:
        self._exit_status = exit_status

    def recv_exit_status(self) -> int:
        """Return the exit status configured for the command.

        Returns
        -------
        int
            Command exit code registered on the fake channel.
        """
        return self._exit_status


class _ReadableStream(io.BytesIO):
    """Bytes stream that mimics Paramiko stdout/stderr handles."""

    def __init__(self, data: str | bytes, exit_status: int = 0) -> None:
        if isinstance(data, str):
            data = data.encode('utf-8')
        super().__init__(data)
        self.channel = _FakeChannel(exit_status)

    def __enter__(self) -> Self:
        """Reset pointer on context entry.

        Returns
        -------
        _ReadableStream
            Stream positioned at the start ready for reading.
        """
        self.seek(0)
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Close the stream on context exit."""
        self.close()


class _WritableStream(io.StringIO):
    """String stream that persists written content into a backing store."""

    def __init__(self, storage: dict[str, str], path: str) -> None:
        super().__init__()
        self._storage = storage
        self._path = path

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Ensure data is flushed to the storage mapping."""
        self.close()

    def close(self) -> None:  # type: ignore[override]
        """Persist the accumulated data when closing."""
        if not self.closed:
            self._storage[self._path] = self.getvalue()
        super().close()

    def __enter__(self) -> Self:
        """Return self for context-manager support.

        Returns
        -------
        _WritableStream
            Stream that buffers written text until close.
        """
        return self


class FakeSFTPClient:
    """Minimal SFTP client stub supporting read/write/stat operations."""

    def __init__(self) -> None:
        self.normalize_path = '/home/test'
        self.files: dict[str, str] = {}
        self.directories: set[str] = {'/'}
        self.open_calls: list[tuple[str, str]] = []
        self.stat_calls: list[str] = []
        self.closed = False

    def normalize(self, path: str) -> str:
        """Mirror Paramiko's normalisation behaviour.

        Returns
        -------
        str
            Normalised path string.
        """
        return self.normalize_path if path == '.' else path

    def stat(self, path: str) -> types.SimpleNamespace:
        """Return stub stat data or raise when the path is missing.

        Returns
        -------
        types.SimpleNamespace
            Minimal stat-like namespace for the requested path.
        """
        self.stat_calls.append(path)
        if path in self.directories or path in self.files:
            return types.SimpleNamespace(st_mode=0)
        raise FileNotFoundError(path)

    def open(self, path: str, mode: str = 'r') -> _ReadableStream | _WritableStream:
        """Return a readable or writable stream backed by in-memory storage.

        Returns
        -------
        _ReadableStream | _WritableStream
            Handle corresponding to the requested access mode.
        """
        self.open_calls.append((path, mode))
        if 'r' in mode:
            if path not in self.files:
                raise FileNotFoundError(path)
            return _ReadableStream(self.files[path])
        return _WritableStream(self.files, path)

    def close(self) -> None:
        """Mark the client as closed."""
        self.closed = True

    def add_file(self, path: str, content: str) -> None:
        """Seed the in-memory file system with a file."""
        self.files[path] = content

    def add_directory(self, path: str) -> None:
        """Register a directory as existing in the fake filesystem."""
        self.directories.add(path)


class FakeSSHClient:
    """Stub of paramiko.SSHClient with configurable command responses."""

    def __init__(self) -> None:
        self.connected = False
        self.policy = None
        self.connect_kwargs: dict[str, Any] | None = None
        self.sftp_client = FakeSFTPClient()
        self.exec_results: dict[str, tuple[str, str, int]] = {}

    def set_missing_host_key_policy(self, policy: Any) -> None:
        """Record the requested host-key policy."""
        self.policy = policy

    def connect(self, **kwargs: Any) -> None:
        """Pretend to establish a connection."""
        self.connected = True
        self.connect_kwargs = kwargs

    def open_sftp(self) -> FakeSFTPClient:
        """Return the in-memory SFTP client.

        Returns
        -------
        FakeSFTPClient
            The shared fake SFTP client instance.
        """
        return self.sftp_client

    def exec_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> tuple[None, _ReadableStream, _ReadableStream]:
        """Return pre-registered command outputs.

        Returns
        -------
        tuple[None, _ReadableStream, _ReadableStream]
            Tuple matching Paramiko's `(stdin, stdout, stderr)` contract.
        """
        del timeout
        stdout_text, stderr_text, exit_status = self.exec_results.get(command, ('', '', 0))
        stdout_stream = _ReadableStream(stdout_text, exit_status)
        stderr_stream = _ReadableStream(stderr_text, exit_status)
        return None, stdout_stream, stderr_stream

    def register_exec_result(self, command: str, stdout: str = '', stderr: str = '', exit_status: int = 0) -> None:
        """Configure the result of a remote command."""
        self.exec_results[command] = (stdout, stderr, exit_status)

    def close(self) -> None:
        """Mark the connection as closed."""
        self.connected = False


@pytest.fixture
def paramiko_fakes(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Patch paramiko SSH primitives with controllable fakes.

    Returns
    -------
    types.SimpleNamespace
        Namespace exposing the fake SSH/SFTP classes and exception types.
    """
    if paramiko is None:
        pytest.skip('paramiko is not available in this environment')

    class FakeSSHError(Exception):
        """Replacement for Paramiko's SSHException."""

    class FakeSFTPError(Exception):
        """Replacement for Paramiko's SFTPError."""

    def _auto_add_policy() -> object:
        """Return a stand-in host-key policy object.

        Returns
        -------
        object
            Marker object used when Paramiko requests a policy instance.
        """
        return object()

    monkeypatch.setattr(paramiko, 'SSHClient', FakeSSHClient)
    monkeypatch.setattr(paramiko, 'AutoAddPolicy', _auto_add_policy)
    monkeypatch.setattr(paramiko, 'SSHException', FakeSSHError, raising=False)
    monkeypatch.setattr(paramiko, 'SFTPError', FakeSFTPError, raising=False)

    return types.SimpleNamespace(
        SSHClient=FakeSSHClient,
        SFTPClient=FakeSFTPClient,
        SSHException=FakeSSHError,
        SFTPError=FakeSFTPError,
    )


# --- Configuration helpers -------------------------------------------------


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the configuration directory to a temporary location.

    Returns
    -------
    Path
        Temporary directory configured for the ASTRA GUI config file.
    """
    config_root = tmp_path / 'astra_config'
    monkeypatch.setenv('ASTRA_GUI_CONFIG_DIR', str(config_root))
    return config_root


def _tk_after(root: TkWidget, _delay: int, callback: Any | None = None, *args: Any) -> str | None:
    """Schedule callbacks immediately for the withdrawn Tk root.

    Returns
    -------
    str | None
        Identifier for the scheduled callback.
    """
    scheduled = getattr(root, 'astra_scheduled_callbacks', None)
    if scheduled is None:
        scheduled = []
        root.astra_scheduled_callbacks = scheduled  # type: ignore[attr-defined]

    if callback is not None:
        scheduled.append((callback, args))
    return f'after#{len(scheduled)}'


def _tk_run_after_callbacks(root: TkWidget, count: int | None = None) -> None:
    """Execute pending callbacks on the withdrawn Tk root."""
    scheduled = getattr(root, 'astra_scheduled_callbacks', [])
    executed = 0
    while scheduled and (count is None or executed < count):
        callback, args = scheduled.pop(0)
        callback(*args)
        executed += 1
