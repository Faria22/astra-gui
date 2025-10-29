import logging
import sys
from collections.abc import Callable
from functools import wraps
from typing import Any


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'ERROR': '\033[38;5;196m',  # Bright Red
        'WARNING': '\033[38;5;208m',  # Bright Orange
        'INFO': '\033[38;5;34m',  # Bright Green
        'DEBUG': '\033[38;5;27m',  # Bright Blue
        'RESET': '\033[0m',  # Reset to default color
    }

    def format(self, record: logging.LogRecord) -> str:
        log_msg = super().format(record)
        color = ColoredFormatter.COLORS.get(record.levelname, ColoredFormatter.COLORS['RESET'])
        return f'{color}{log_msg}{ColoredFormatter.COLORS["RESET"]}'


# Creates a custom error function to automatically exit the code
class CustomLogger(logging.Logger):
    def error(self, msg, *args, **kwargs) -> None:  # noqa: ANN001
        if 'stacklevel' not in kwargs:
            kwargs['stacklevel'] = 2
        super().error(msg, *args, **kwargs)
        sys.exit(1)  # Exit with error code 1


def setup_logger(debug: bool) -> None:
    # Create the root logger and set its level
    logging.setLoggerClass(CustomLogger)
    logger = logging.getLogger()  # Root logger

    logger.setLevel(logging.DEBUG if debug else logging.WARNING)

    if logger.hasHandlers():
        logger.handlers.clear()

    # Set up the console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.WARNING)

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
    """Log before and after operations."""
    logger = logging.getLogger(__name__)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
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
