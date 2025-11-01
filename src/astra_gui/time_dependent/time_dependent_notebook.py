"""Notebook that aggregates pages for time-dependent calculations."""

from tkinter import ttk
from typing import TYPE_CHECKING

from astra_gui.utils.notebook_module import Notebook

from .pulse import PulsePage
from .td_notebook_page_module import TdNotebookPage

if TYPE_CHECKING:
    from astra_gui.app import Astra


class TimeDependentNotebook(Notebook[TdNotebookPage]):
    """Container notebook for time-dependent workflows."""

    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        """Initialise the notebook and add the pulse configuration page."""
        super().__init__(parent, controller, 'Run Time Independent Programs')

        self.add_pages([PulsePage])

    def reset(self) -> None:
        """Reset the notebook to its default state."""
        self.erase()
