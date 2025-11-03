"""Logging utilities with colourised output and helper decorators."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

_HANDLER_STATE: dict[str, logging.Handler | None] = {'managed': None}


class ColoredFormatter(logging.Formatter):
    """Format log messages using ANSI colours for readability."""

    COLORS = {
        'ERROR': '\033[38;5;196m',  # Bright Red
        'WARNING': '\033[38;5;208m',  # Bright Orange
        'INFO': '\033[38;5;34m',  # Bright Green
        'DEBUG': '\033[38;5;27m',  # Bright Blue
        'RESET': '\033[0m',  # Reset to default color
    }

    def format(self, record: logging.LogRecord) -> str:
        """Wrap the formatted log message in the appropriate colour codes.

        Returns
        -------
        str
            Colourised log message ready for output.
        """
        log_msg = super().format(record)
        color = ColoredFormatter.COLORS.get(record.levelname, ColoredFormatter.COLORS['RESET'])
        return f'{color}{log_msg}{ColoredFormatter.COLORS["RESET"]}'


_OPERATION_LINE_LENGTH = 100
_OPERATION_ELLIPSIS_THRESHOLD = 3


def _format_operation_banner(message: str, *, fill_char: str) -> str:
    """Return a fixed-width banner with centred message for operation logs.

    Returns
    -------
    str
        The banner line padded with the requested fill character.
    """
    if not fill_char:
        fill_char = '-'
    char = fill_char[0]

    max_message_length = max(_OPERATION_LINE_LENGTH - 4, 0)
    display_message = message
    if len(display_message) > max_message_length > _OPERATION_ELLIPSIS_THRESHOLD:
        display_message = f'{display_message[: max_message_length - _OPERATION_ELLIPSIS_THRESHOLD]}...'

    text = f' {display_message} '

    return text.center(_OPERATION_LINE_LENGTH, char)


def setup_logger(*, debug: bool = False, verbose: bool = False, quiet: bool = False) -> None:
    """Configure the root logger and attach a colourised console handler.

    Existing handlers that were not installed by this helper are preserved.
    """
    # Create the root logger and set its level
    logger = logging.getLogger()  # Root logger

    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    elif quiet:
        level = logging.ERROR
    else:
        level = logging.WARNING

    logger.setLevel(level)

    for handler in list(logger.handlers):
        if getattr(handler, 'astra_managed', False):
            logger.removeHandler(handler)

    # Set up the console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # Choose the format based on debug mode
    if debug:
        # Detailed format for debug mode
        formatter = ColoredFormatter('%(levelname)s: %(message)s | [%(name)s] %(funcName)s: %(lineno)d')
    else:
        # Simpler format for normal mode
        formatter = ColoredFormatter('%(levelname)s: %(message)s')

    ch.setFormatter(formatter)
    ch.set_name('astra_gui.console')
    ch.astra_managed = True  # type: ignore[attr-defined]
    logger.addHandler(ch)
    _HANDLER_STATE['managed'] = ch


def log_operation(operation: str) -> Any:
    """Log start and finish messages around a callable.

    Returns
    -------
    Callable[..., Any]
        Decorator that wraps the target callable.
    """
    logger = logging.getLogger(__name__)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap the provided function with pre/post logging statements.

        Returns
        -------
        Callable[..., Any]
            Wrapped function with logging side-effects.
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_message = _format_operation_banner(f'Started {operation}.', fill_char='*')
            finish_message = _format_operation_banner(f'Finished {operation}.', fill_char='-')

            logger.debug(start_message, stacklevel=2)
            result = func(*args, **kwargs)
            logger.debug(finish_message, stacklevel=2)
            return result

        return wrapper

    return decorator


def get_managed_handler() -> logging.Handler | None:
    """Return the handler managed by setup_logger, if any.

    Returns
    -------
    logging.Handler | None
        Managed handler instance when available, otherwise ``None``.
    """
    return _HANDLER_STATE['managed']


if __name__ == '__main__':
    # Set up logger with debug mode if needed
    setup_logger(debug=True)  # Or False for non-debug

    logger = logging.getLogger(__name__)

    logger.error('This is an error message.')
    logger.info('This is an info message.')
    logger.debug('This is a debug message.')
    logger.warning('This is a warning message.')
