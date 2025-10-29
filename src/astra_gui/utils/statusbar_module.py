import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class StatusBar(ttk.Label):
    def __init__(self, root: tk.Tk, default_text: str) -> None:
        super().__init__(root, text=default_text, anchor=tk.W)

        self.root = root
        self.default_message = default_text
        self.message_queue: list[tuple[str, int]] = []
        self.is_displaying_message = False

    def show_message(
        self,
        message: str,
        overwrite_default_text: bool = False,
        time: int = 0,
    ) -> None:
        """Add message to the queue."""
        if overwrite_default_text:
            self.default_message = message

        self.message_queue.append((message, time))

        if not self.is_displaying_message:
            self.is_displaying_message = True
            self.show_next_message()

    def show_next_message(self) -> None:
        """Display the next message in the queue."""
        if self.message_queue:
            message, time = self.message_queue.pop()
            self.config(text=message)
            logger.info('Changed statusbar to %s', message)
            self.root.after(time * 1000, self.reset_message)

    def reset_message(self) -> None:
        """Reset to the default message."""
        if self.message_queue:
            self.show_next_message()
            return

        logger.info('Changed statusbar to default message: %s', self.default_message)
        self.config(text=self.default_message)
        self.is_displaying_message = False
