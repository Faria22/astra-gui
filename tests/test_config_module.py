"""Tests for the shared ASTRA GUI configuration file."""

import sys
from pathlib import Path

import pytest

try:
    from astra_gui.utils import config_module
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils import config_module


def _set_config_dir(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    """Point the configuration helper to a temporary directory."""
    monkeypatch.setenv(config_module.ENV_CONFIG_DIR, str(directory))


def test_set_and_get_notification_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure notification settings round-trip via the config file."""
    config_dir = tmp_path / 'config'
    _set_config_dir(monkeypatch, config_dir)

    config_module.set_notification_settings('email', 'user@example.com')

    settings = config_module.get_notification_settings()
    assert settings['method'] == 'email'
    assert settings['string'] == 'user@example.com'

    config_path = config_dir / config_module.CONFIG_FILENAME
    assert config_path.is_file()
    contents = config_path.read_text(encoding='utf-8')
    assert 'email' in contents
    assert 'user@example.com' in contents


def test_set_ssh_host_preserves_notification_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure storing SSH host does not clobber notification settings."""
    config_dir = tmp_path / 'cfg'
    _set_config_dir(monkeypatch, config_dir)

    config_module.set_notification_settings('ntfy', 'topic')
    config_module.set_ssh_host('astra-host')

    settings = config_module.get_notification_settings()
    assert settings['method'] == 'ntfy'
    assert settings['string'] == 'topic'

    assert config_module.get_ssh_host() == 'astra-host'
