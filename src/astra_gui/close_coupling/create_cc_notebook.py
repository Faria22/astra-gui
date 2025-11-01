"""Notebook that groups pages used to set up close-coupling calculations."""

from tkinter import ttk
from typing import TYPE_CHECKING

from astra_gui.utils.notebook_module import Notebook

from .bsplines import Bsplines
from .cc_notebook_page_module import CcNotebookPage
from .clscplng import Clscplng
from .dalton import Dalton
from .lucia import Lucia
from .molecule import Molecule

if TYPE_CHECKING:
    from astra_gui.app import Astra


class CreateCcNotebook(Notebook[CcNotebookPage]):
    """Top-level notebook that walks the user through CC preparation steps."""

    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        """Initialise the notebook and load all close-coupling pages."""
        super().__init__(parent, controller, 'Create Close Coupling')

        self.reset()

        self.add_pages([Molecule, Dalton, Lucia, Clscplng, Bsplines])

    def reset(self) -> None:
        """Reset shared data structures and clear each page."""
        # Defines default values for those that need to be shared across notebookPages
        self.molecule_data: dict[str, str | int | bool] = {
            'basis': '6-311G',
            'description': '',
            'accuracy': '1.00D-10',
            'units': 'Angstrom',
            'number_atoms': 0,
            'linear_molecule': False,
            'generators': '',
        }
        self.dalton_data: dict[str, str | int] = {'ref_sym': 1, 'doubly_occupied': ''}
        self.lucia_data: dict[str, str | int | list[str]] = {
            'lcsblk': 106968,
            'electrons': 0,
            'total_orbitals': [],
            'states': [],
            'energies': [],
            'relative_energies': [],
        }
        self.cc_data: dict[str, int | list[str]] = {'lmax': 3, 'total_syms': []}

        self.erase()
