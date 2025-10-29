from tkinter import ttk
from typing import TYPE_CHECKING

from notebook_module import Notebook

from .pulse import PulsePage
from .td_notebook_page_module import TdNotebookPage

if TYPE_CHECKING:
    from main import Astra


class TimeDependentNotebook(Notebook[TdNotebookPage]):
    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        super().__init__(parent, controller, 'Run Time Independent Programs')

        self.add_pages([PulsePage])

    def reset(self) -> None:
        self.erase()
