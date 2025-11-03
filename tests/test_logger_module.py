"""Validate the logger configuration entry points exposed to the CLI."""

import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

try:
    from astra_gui.utils.logger_module import get_managed_handler, log_operation, setup_logger
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.utils.logger_module import get_managed_handler, log_operation, setup_logger


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
    for handler in logging.getLogger().handlers:
        if getattr(handler, 'astra_managed', False):
            return handler
    if (managed := get_managed_handler()) is not None:
        return managed
    msg = 'Managed handler not installed on root logger'
    raise AssertionError(msg)


def clear_root_handlers() -> None:
    """Remove all handlers from the root logger for deterministic testing."""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)


def test_setup_logger_defaults_to_warning_level() -> None:
    """Root logger defaults to warning level when no flags are provided."""
    clear_root_handlers()
    setup_logger()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING
    assert get_root_handler().level == logging.WARNING


def test_setup_logger_verbose_sets_info_level() -> None:
    """Verbose flag promotes logging to INFO."""
    clear_root_handlers()
    setup_logger(verbose=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert get_root_handler().level == logging.INFO


def test_setup_logger_quiet_sets_error_level() -> None:
    """Quiet flag demotes logging to ERROR."""
    clear_root_handlers()
    setup_logger(quiet=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.ERROR
    assert get_root_handler().level == logging.ERROR


def test_setup_logger_debug_sets_debug_level_and_format() -> None:
    """Debug flag enables DEBUG output and detailed formatter."""
    clear_root_handlers()
    setup_logger(debug=True)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    handler = get_root_handler()
    assert handler.level == logging.DEBUG
    assert handler.formatter is not None


def test_setup_logger_preserves_external_handlers() -> None:
    """setup_logger should leave user-installed handlers intact."""
    root_logger = logging.getLogger()
    clear_root_handlers()
    sentinel = logging.NullHandler()
    root_logger.addHandler(sentinel)

    setup_logger()

    assert sentinel in root_logger.handlers


def test_setup_logger_is_idempotent() -> None:
    """Repeated calls should replace the managed handler rather than stacking."""
    clear_root_handlers()
    setup_logger()
    setup_logger(verbose=True)

    managed_handlers = [
        handler for handler in logging.getLogger().handlers if getattr(handler, 'astra_managed', False)
    ]
    assert len(managed_handlers) == 1
    assert managed_handlers[0].level == logging.INFO


def test_log_operation_emits_start_and_finish_logs() -> None:
    """log_operation should wrap the callable with start/finish debug logs."""
    clear_root_handlers()
    setup_logger(debug=True)
    records: list[logging.LogRecord] = []

    class CollectingHandler(logging.Handler):
        def __init__(self, target: list[logging.LogRecord]) -> None:
            super().__init__()
            self._records = target

        def emit(self, record: logging.LogRecord) -> None:
            self._records.append(record)

    capture_handler = CollectingHandler(records)
    capture_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(capture_handler)
    try:
        @log_operation('sample task')
        def sample() -> str:
            return 'done'

        assert sample() == 'done'
    finally:
        logging.getLogger().removeHandler(capture_handler)

    messages = [record.getMessage() for record in records]
    assert any('Started sample task.' in message for message in messages)
    assert any('Finished sample task.' in message for message in messages)
