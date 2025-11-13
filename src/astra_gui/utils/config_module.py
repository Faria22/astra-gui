"""Helpers for reading and writing the ASTRA GUI configuration file."""

import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import toml

logger = logging.getLogger(__name__)

CONFIG_FILENAME = 'config.toml'
CONFIG_DIRECTORY_NAME = 'astra_gui'
ENV_CONFIG_DIR = 'ASTRA_GUI_CONFIG_DIR'
NOTIFICATION_SECTION = 'notification'
SSH_SECTION = 'ssh'


def get_config_directory() -> Path:
    """Return the directory that should contain the config file.

    Returns
    -------
    Path
        Directory where the ASTRA GUI configuration file should live.
    """
    if env_dir := os.getenv(ENV_CONFIG_DIR):
        return Path(env_dir).expanduser()

    if sys.platform == 'win32':
        base_dir = os.getenv('APPDATA')
        if base_dir:
            return Path(base_dir) / CONFIG_DIRECTORY_NAME
        return Path.home() / 'AppData' / 'Roaming' / CONFIG_DIRECTORY_NAME

    if xdg_dir := os.getenv('XDG_CONFIG_HOME'):
        return Path(xdg_dir).expanduser() / CONFIG_DIRECTORY_NAME

    return Path.home() / '.config' / CONFIG_DIRECTORY_NAME


def get_config_path() -> Path:
    """Return the full path to the config file.

    Returns
    -------
    Path
        Absolute path to the configuration file.
    """
    return get_config_directory() / CONFIG_FILENAME


def load_config() -> dict[str, Any]:
    """Load the configuration file, returning an empty dict if missing.

    Returns
    -------
    dict[str, Any]
        Parsed TOML configuration data; empty if file is missing or invalid.
    """
    config_path = get_config_path()
    if not config_path.is_file():
        return {}

    try:
        with config_path.open('r', encoding='utf-8') as file:
            data = toml.load(file)
    except (OSError, toml.TomlDecodeError) as exc:
        logger.error('Unable to read config file at %s: %s', config_path, exc)
        return {}

    if not isinstance(data, dict):
        logger.error('Config file %s did not contain a mapping.', config_path)
        return {}

    return data


def save_config(config: Mapping[str, Any]) -> None:
    """Persist the provided config mapping to disk."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug('Persisting config to %s', config_path)
    try:
        with config_path.open('w', encoding='utf-8') as file:
            toml.dump(dict(config), file)
    except (OSError, TypeError) as exc:
        logger.error('Failed to write config file at %s: %s', config_path, exc)
        raise


def get_notification_settings() -> dict[str, str]:
    """Return stored notification settings.

    Returns
    -------
    dict[str, str]
        Mapping with keys ``method`` and ``string`` describing notification hooks.
    """
    config = load_config()
    section = config.get(NOTIFICATION_SECTION, {})
    if not isinstance(section, dict):
        logger.error('Notification section malformed; resetting.')
        return {'method': '', 'string': ''}

    method = str(section.get('method', '') or '')
    notification_string = str(section.get('string', '') or '')
    return {'method': method, 'string': notification_string}


def set_notification_settings(method: str, notification_string: str) -> None:
    """Store notification settings in the config file."""
    config = load_config()
    config[NOTIFICATION_SECTION] = {
        'method': method,
        'string': notification_string,
    }
    save_config(config)


def get_ssh_host() -> str:
    """Return stored SSH host name, if any.

    Returns
    -------
    str
        SSH host nickname saved in the configuration file, or an empty string.
    """
    config = load_config()
    section = config.get(SSH_SECTION, {})
    if isinstance(section, dict):
        return str(section.get('host', '') or '')

    logger.error('SSH section malformed; resetting.')
    return ''


def set_ssh_host(host_name: str) -> None:
    """Persist the SSH host name to the config file."""
    logger.info('Persisting SSH host "%s" to config section %s', host_name, SSH_SECTION)
    config = load_config()
    config[SSH_SECTION] = {'host': host_name}
    save_config(config)


__all__ = [
    'CONFIG_FILENAME',
    'ENV_CONFIG_DIR',
    'NOTIFICATION_SECTION',
    'SSH_SECTION',
    'get_config_directory',
    'get_config_path',
    'get_notification_settings',
    'get_ssh_host',
    'load_config',
    'save_config',
    'set_notification_settings',
    'set_ssh_host',
]
