"""Notebook that groups pages used to set up close-coupling calculations."""

from tkinter import ttk
from typing import TYPE_CHECKING, TypedDict

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
            accuracy='1.00D-10',
            units='Angstrom',
            number_atoms=0,
            linear_molecule=False,
            generators='',
            geom_label='',
            atoms_data='',
            num_diff_atoms=0,
        )
        self.dalton_data = DaltonData(
            basis='6-311G',
            description='',
            doubly_occupied='',
            orbital_energies='',
            state_sym=0,
            multiplicity=0,
            electrons=0,
            doubly='',
            singly='',
        )
        self.lucia_data = LuciaData(
            lcsblk=106968,
            electrons=0,
            total_orbitals=[],
            states=[],
            energies=[],
            relative_energies=[],
        )
        self.cc_data = CcData(lmax=3, total_syms=[])

        self.erase()


class MoleculeData(TypedDict):
    """Shared molecular metadata tracked across close-coupling pages."""

    accuracy: str
    units: str
    number_atoms: int
    linear_molecule: bool
    generators: str
    geom_label: str
    atoms_data: str
    num_diff_atoms: int


class DaltonData(TypedDict):
    """State propagated between Dalton configuration steps and outputs."""

    basis: str
    description: str
    doubly_occupied: str
    orbital_energies: str
    state_sym: int
    multiplicity: int
    electrons: int
    doubly: str
    singly: str


class LuciaData(TypedDict):
    """Aggregated Lucia calculation configuration and results."""

    lcsblk: int
    electrons: int
    total_orbitals: list[str]
    states: list[str]
    energies: list[str]
    relative_energies: list[str]


class CcData(TypedDict):
    """Close-coupling metadata shared with downstream notebooks."""

    lmax: int
    total_syms: list[str]
