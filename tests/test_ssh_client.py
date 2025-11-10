"""Tests for the SSH client utilities used by the GUI."""

import sys
from pathlib import Path
from typing import Any, cast

import pytest

try:
    from astra_gui.utils.ssh_client import SftpContext, SshClient
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils.ssh_client import SftpContext, SshClient

from tests.conftest import DialogSpy, FakeSFTPClient, FakeSSHClient


def make_ssh_client() -> SshClient:
    """Create an SSH client instance without triggering GUI initialisation.

    Returns
    -------
    SshClient
        Uninitialised SSH client populated with fake dependencies.
    """
    client = SshClient.__new__(SshClient)
    client.root = DialogSpy(Path.cwd())  # type: ignore[attr-defined]
    client.host_name = ''
    client.username = ''
    client.client = None
    client.notification = None  # type: ignore[attr-defined]
    client.home_path = None  # type: ignore[attr-defined]
    return client


@pytest.fixture
def ssh_client() -> SshClient:
    """Return an SSH client backed by fake Paramiko primitives.

    Returns
    -------
    SshClient
        Fresh SSH client instance using the fake Paramiko wiring.
    """
    return make_ssh_client()


def test_path_exists_without_client_returns_false(ssh_client: SshClient) -> None:
    """Absent SSH client should cause existence checks to return False."""
    assert ssh_client.path_exists(Path('/remote/path')) is False


def test_path_exists_checks_remote_stat(ssh_client: SshClient) -> None:
    """Remote stat should be delegated to the SFTP client."""
    fake_ssh = FakeSSHClient()
    fake_ssh.sftp_client.add_directory('/remote/dir')
    ssh_client.client = cast(Any, fake_ssh)

    assert ssh_client.path_exists(Path('/remote/dir')) is True
    assert fake_ssh.sftp_client.stat_calls[-1] == '/remote/dir'
    assert fake_ssh.sftp_client.closed is True


def test_read_from_file_returns_decoded_text(ssh_client: SshClient) -> None:
    """Reading with decode=True should return text."""
    fake_ssh = FakeSSHClient()
    fake_ssh.sftp_client.add_file('/remote/file.txt', 'hello world')
    ssh_client.client = cast(Any, fake_ssh)

    content = ssh_client.read_from_file(Path('/remote/file.txt'))
    assert content == 'hello world'
    assert fake_ssh.sftp_client.open_calls[-1] == ('/remote/file.txt', 'r')


def test_read_from_file_binary_mode(ssh_client: SshClient) -> None:
    """Reading with decode=False should return bytes."""
    fake_ssh = FakeSSHClient()
    fake_ssh.sftp_client.add_file('/remote/data.bin', 'binary')
    ssh_client.client = cast(Any, fake_ssh)

    content = ssh_client.read_from_file(Path('/remote/data.bin'), decode=False)
    assert content == b'binary'


def test_read_from_missing_file_returns_empty_string(ssh_client: SshClient) -> None:
    """Missing files should result in an empty string."""
    fake_ssh = FakeSSHClient()
    ssh_client.client = cast(Any, fake_ssh)

    assert not ssh_client.read_from_file(Path('/remote/missing.txt'))


def test_write_to_file_overwrites_content(ssh_client: SshClient) -> None:
    """Writing to an existing directory should persist the content."""
    fake_ssh = FakeSSHClient()
    fake_ssh.sftp_client.add_directory('/remote')
    ssh_client.client = cast(Any, fake_ssh)

    ssh_client.write_to_file(Path('/remote/output.txt'), 'payload')
    assert fake_ssh.sftp_client.files['/remote/output.txt'] == 'payload'
    assert fake_ssh.sftp_client.open_calls[-1] == ('/remote/output.txt', 'w')


def test_write_to_missing_directory_logs_warning(ssh_client: SshClient) -> None:
    """Writing to a missing directory should not create the file."""
    fake_ssh = FakeSSHClient()
    ssh_client.client = cast(Any, fake_ssh)

    ssh_client.write_to_file(Path('/missing/output.txt'), 'payload')
    assert '/missing/output.txt' not in fake_ssh.sftp_client.files


def test_run_remote_command_without_client_returns_error(ssh_client: SshClient) -> None:
    """Missing SSH client should produce an error return tuple."""
    assert ssh_client.run_remote_command('ls') == ('', '', -1)


def test_run_remote_command_collects_stdout_and_stderr(ssh_client: SshClient, caplog: pytest.LogCaptureFixture) -> None:
    """Remote command execution should expose stdout, stderr, and exit status."""
    fake_ssh = FakeSSHClient()
    expected_exit_code = 7
    fake_ssh.register_exec_result('ls', stdout='out', stderr='warn', exit_status=expected_exit_code)
    ssh_client.client = cast(Any, fake_ssh)

    caplog.set_level('WARNING')
    stdout, stderr, exit_code = ssh_client.run_remote_command('ls')

    assert stdout == 'out'
    assert stderr == 'warn'
    assert exit_code == expected_exit_code
    assert 'SSH command stderr' in caplog.text


def test_sftp_context_closes_session() -> None:
    """Context manager should close the SFTP session even on success."""
    fake_ssh = FakeSSHClient()

    with SftpContext(cast(Any, fake_ssh)) as sftp:
        assert isinstance(sftp, FakeSFTPClient)
        assert sftp.closed is False

    assert fake_ssh.sftp_client.closed is True
