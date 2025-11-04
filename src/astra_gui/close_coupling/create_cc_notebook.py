"""Notebook that groups pages used to set up close-coupling calculations."""

from tkinter import ttk
from typing import TYPE_CHECKING, cast

from astra_gui.utils.notebook_module import Notebook

from .bsplines import Bsplines
from .cc_notebook_page_module import CcNotebookPage
from .clscplng import Clscplng
from .dalton import Dalton
from .lucia import Lucia
from .molecule import Molecule
from .notebook_state import CcData, DaltonData, LuciaData, MoleculeData

if TYPE_CHECKING:
    from astra_gui.app import Astra


class CreateCcNotebook(Notebook[CcNotebookPage]):
    """Top-level notebook that walks the user through CC preparation steps."""

    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        """Initialise the notebook and load all close-coupling pages."""
        super().__init__(parent, controller, 'Create Close Coupling')

        self.molecule_data: MoleculeData
        self.dalton_data: DaltonData
        self.lucia_data: LuciaData
        self.cc_data: CcData

        self.reset()

        self.add_pages([Molecule, Dalton, Lucia, Clscplng, Bsplines])

    def reset(self) -> None:
        """Reset shared data structures and clear each page."""
        # Defines default values for those that need to be shared across notebookPages
        self.molecule_data = MoleculeData(
            basis='6-311G',
            description='',
            accuracy='1.00D-10',
            units='Angstrom',
            number_atoms=0,
            linear_molecule=False,
            generators='',
        )
        self.dalton_data = DaltonData(ref_sym=1, doubly_occupied='')
        self.lucia_data = LuciaData(
            lcsblk=106968,
            electrons=0,
            total_orbitals=cast(list[str], []),
            states=cast(list[str], []),
            energies=cast(list[str], []),
            relative_energies=cast(list[str], []),
        )
        self.cc_data = CcData(lmax=3, total_syms=cast(list[str], []))

        self.erase()
