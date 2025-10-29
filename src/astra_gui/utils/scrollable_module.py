"""Scrollable frame/treeview helpers built atop Tkinter widgets."""

import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar that hosts arbitrary widgets."""

    def __init__(self, master: ttk.Frame, height: int = 300) -> None:
        """Initialise the canvas-backed frame and attach scroll bindings."""
        super().__init__(master)

        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)

        # Create a frame inside the canvas
        self.inner_frame = ttk.Frame(self.canvas)

        # Add the frame to the canvas
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack the canvas and scrollbar
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        # Bind the configure event to update the canvas scroll region
        self.inner_frame.bind('<Configure>', self._on_frame_configure)

    def _on_frame_configure(self, _event: tk.Event) -> None:
        """Update the canvas scroll region whenever children resize."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.canvas.config(width=self.inner_frame.winfo_reqwidth())


class ScrollableTreeview(ttk.Treeview):
    """Treeview widget that automatically adds a vertical scrollbar."""

    def __init__(self, parent_frame: ttk.Frame, *args, **kwargs) -> None:
        """Create the treeview and pack an attached scrollbar."""
        super().__init__(parent_frame, *args, **kwargs)

        vsb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.yview)
        vsb.pack(side=tk.RIGHT, fill='y')

        self.configure(yscrollcommand=vsb.set)
