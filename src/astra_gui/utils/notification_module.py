"""Helpers for configuring notification hooks used by the GUI."""

import logging
from pathlib import Path
from tkinter import messagebox

from .logger_module import log_operation

logger = logging.getLogger(__name__)


class Notification:
    """Persist and generate commands for external notifications."""

    def __init__(self, input_file: Path) -> None:
        """Load the saved notification method from `input_file` if present."""
        self.input_file = input_file
        self.method = ''  # Either ntfy or email
        self.string = ''  # Either ntfy topic or email address

        self.load()

    @log_operation('saving notification method')
    def save(self, notification_string: str) -> None:
        """Persist the notification method and address/endpoint to disk."""
        if not notification_string:
            messagebox.showwarning('Missing string!', 'String was not given')
            return

        self.notification_string = notification_string

        with self.input_file.open('w') as f:
            f.write(f'{self.method}\n{notification_string}')

    @log_operation('loading notification file')
    def load(self) -> None:
        """Load notification settings from disk, if the file exists."""
        if self.input_file.is_file():
            with self.input_file.open('r') as f:
                lines = f.read().split('\n')
                self.method = lines[0].strip()
                self.string = lines[1].strip()

    def command(self, title: str) -> str:
        """Return notification command to add to script.

        Returns
        -------
        str
            Shell command string for ntfy or email notifications.
        """
        message = f'{title} has finished!  It took ${{hours}} hours and ${{minutes}} minutes to run.'
        message_title = 'ASTRA GUI Notification'
        if self.method == 'ntfy':
            return f'curl -d "{message}" -H "Title: {message_title}" https://ntfy.sh/{self.string} > /dev/null 2>&1'
        if self.method == 'email':
            return f'echo "{message}" | mail -s "{message_title}" {self.string}'

        logger.error('Unsupported notification method: %s.', self.method)
        return ''
