"""TypedDict definitions for close-coupling notebook shared state."""

from typing import NotRequired, TypedDict


class MoleculeData(TypedDict):
    """Shared molecular metadata tracked across close-coupling pages."""

    basis: str
    description: str
    accuracy: str
    units: str
    number_atoms: int
    linear_molecule: bool
    generators: str
    geom_label: NotRequired[str]
    atoms_data: NotRequired[str]
    num_diff_atoms: NotRequired[int]


class DaltonData(TypedDict):
    """State propagated between Dalton configuration steps and outputs."""

    ref_sym: int
    doubly_occupied: str
    orbital_energies: NotRequired[str]
    symmetry: NotRequired[int]
    multiplicity: NotRequired[str]
    electrons: NotRequired[str]
    doubly: NotRequired[str]
    singly: NotRequired[str]


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
