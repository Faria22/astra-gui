"""Helpers for configuring notification hooks used by the GUI."""

import logging
from tkinter import messagebox

from .config_module import get_notification_settings, set_notification_settings
from .logger_module import log_operation

logger = logging.getLogger(__name__)


class Notification:
    """Persist and generate commands for external notifications."""

    def __init__(self) -> None:
        """Load saved notification settings."""
        self.method = ''  # Either ntfy or email
        self.string = ''  # Either ntfy topic or email address

        self.load()

    @log_operation('saving notification method')
    def save(self, notification_string: str) -> None:
        """Persist the notification method and address/endpoint to disk."""
        if not notification_string:
            messagebox.showwarning('Missing string!', 'String was not given')
            return

        self.string = notification_string
        set_notification_settings(self.method, notification_string)

    @log_operation('loading notification file')
    def load(self) -> None:
        """Load notification settings from disk."""
        settings = get_notification_settings()
        self.method = settings.get('method', '')
        self.string = settings.get('string', '')

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
