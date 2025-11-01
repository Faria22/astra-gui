"""Logging utilities with colourised output and helper decorators."""

import logging
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any


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


# Creates a custom error function to automatically exit the code
class CustomLogger(logging.Logger):
    """Logger that exits the process whenever an error is emitted."""

    def error(self, msg, *args, **kwargs) -> None:  # noqa: ANN001
        """Log an error and terminate the process with exit code 1."""
        if 'stacklevel' not in kwargs:
            kwargs['stacklevel'] = 2
        super().error(msg, *args, **kwargs)
        sys.exit(1)  # Exit with error code 1


logging.setLoggerClass(CustomLogger)

def setup_logger(*, debug: bool = False, verbose: bool = False, quiet: bool = False) -> None:
    """Configure the root logger and attach a colourised console handler."""
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

    if logger.hasHandlers():
        logger.handlers.clear()

    # Set up the console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # Choose the format based on debug mode
    if debug:
        # Detailed format for debug mode
        formatter = ColoredFormatter('%(levelname)s: %(message)s | %(filename)s - %(funcName)s: %(lineno)d')
    else:
        # Simpler format for normal mode
        formatter = ColoredFormatter('%(levelname)s: %(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)


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
            logger.info('******************** Started %s.  ********************', operation, stacklevel=2)
            result = func(*args, **kwargs)
            logger.info('-------------------- Finished %s. --------------------', operation, stacklevel=2)
            return result

        return wrapper

    return decorator


if __name__ == '__main__':
    # Set up logger with debug mode if needed
    setup_logger(debug=True)  # Or False for non-debug

    logger = logging.getLogger(__name__)

    logger.error('This is an error message.')
    logger.info('This is an info message.')
    logger.debug('This is a debug message.')
    logger.warning('This is a warning message.')
