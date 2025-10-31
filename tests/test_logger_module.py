"""Validate the logger configuration entry points exposed to the CLI."""

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

try:
    from astra_gui.utils.logger_module import setup_logger
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils.logger_module import setup_logger


@pytest.fixture(autouse=True)
def restore_logging_state() -> Iterator[None]:
    """Ensure each test starts with a clean logging configuration.

    Yields
    ------
    None
        Allows the test to run with a clean logging configuration.
    """
    # Snapshot the logger configuration so each test can mutate it freely.
    original_class = logging.getLoggerClass()
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = list(root_logger.handlers)

    # Yield control to the test.
    yield

    # Restore the original logging configuration to avoid cross-test pollution.
    logging.setLoggerClass(original_class)
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


def get_root_handler() -> logging.Handler:
    """Return the root logger handler added by setup_logger.

    Returns
    -------
    logging.Handler
        Handler attached to the root logger.
    """
    handler, *_ = logging.getLogger().handlers
    return handler


def test_setup_logger_defaults_to_warning_level() -> None:
    """Root logger defaults to warning level when no flags are provided."""
    setup_logger()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING
    assert get_root_handler().level == logging.WARNING


def test_setup_logger_verbose_sets_info_level() -> None:
    """Verbose flag promotes logging to INFO."""
    setup_logger(verbose=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert get_root_handler().level == logging.INFO


def test_setup_logger_quiet_sets_error_level() -> None:
    """Quiet flag demotes logging to ERROR."""
    setup_logger(quiet=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.ERROR
    assert get_root_handler().level == logging.ERROR


def test_setup_logger_debug_sets_debug_level_and_format() -> None:
    """Debug flag enables DEBUG output and detailed formatter."""
    setup_logger(debug=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    handler = get_root_handler()
    assert handler.level == logging.DEBUG
    assert handler.formatter is not None
