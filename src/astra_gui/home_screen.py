from tkinter import ttk
from typing import TYPE_CHECKING

from notebook_module import Notebook

if TYPE_CHECKING:
    from main import Astra


class HomeNotebook(Notebook):
    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        super().__init__(parent, controller, 'ASTRA', pack_notebook=False)

        ttk.Button(
            self.notebook_frame,
            text='Create Close Coupling',
            command=lambda: controller.show_notebook(1),
        ).pack(pady=5)
        ttk.Button(
            self.notebook_frame,
            text='Time Independent Calculations',
            command=lambda: controller.show_notebook(2),
        ).pack(pady=5)
        ttk.Button(
            self.notebook_frame,
            text='Time Dependent Calculations',
            command=lambda: controller.show_notebook(3),
        ).pack(pady=5)

    def reset(self) -> None: ...
