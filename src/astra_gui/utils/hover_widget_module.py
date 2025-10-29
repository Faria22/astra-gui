"""Utility for adding hover tooltips to Tk widgets."""

import tkinter as tk
from tkinter import ttk


class HoverWidgetClass:
    """Wrap a widget factory with simple hover-text behaviour."""

    def __init__(
        self,
        widget: type[ttk.Widget],
        frame: ttk.Frame,
        hover_text: str,
        **kwargs,
    ) -> None:
        """Create the widget and register enter/leave bindings."""
        self.widget = widget(frame, **kwargs)
        self.hover_text = hover_text
        self.popup: tk.Toplevel | None = None

        self.widget.bind('<Enter>', self.show_hover_text)
        self.widget.bind('<Leave>', self.hide_hover_text)

    def show_hover_text(self, _event: tk.Event) -> None:
        """Display the hover popup if it is not already visible."""
        if self.popup:
            return

        x_shift = 5
        y_shift = -10

        x = self.widget.winfo_rootx() + self.widget.winfo_width() + x_shift
        y = self.widget.winfo_rooty() + y_shift
        self.popup = tk.Toplevel(self.widget)
        self.popup.wm_overrideredirect(True)
        self.popup.wm_geometry(f'+{x}+{y}')

        ttk.Label(self.popup, text=self.hover_text).pack(padx=5, pady=5)

    def hide_hover_text(self, _event: tk.Event) -> None:
        """Destroy the hover popup when the cursor leaves the widget."""
        if self.popup:
            self.popup.destroy()
            self.popup = None
