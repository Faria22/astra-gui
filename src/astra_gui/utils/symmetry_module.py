import logging
from collections import Counter
from itertools import combinations

logger = logging.getLogger(__name__)


class Symmetry:  # noqa: PLW1641
    GROUPS = (
        'C1',
        'Cs',
        'C2',
        'Ci',
        'C2v',
        # 'C2h',
        'D2',
        'D2h',
    )

    def __init__(self, group: str) -> None:
        group = group.capitalize()
        if group not in self.GROUPS:
            logger.error('Invalid symmetry group: %s', group)

        self.group = group
        self.generators = self.get_generators()
        self.irrep = self.get_irrep()
        self.dipole = self.get_dipoles()
        self.mult_table = self.get_mult_table()

    def __repr__(self) -> str:
        return f'Symmetry(group: {self.group}, irrep: {self.irrep})'

    def get_generators(self) -> list[str]:
        generators = {
            'C1': [],
            'Cs': ['Z'],
            'C2': ['XY'],
            'Ci': ['XYZ'],
            'C2v': ['X', 'Y'],
            'C2h': ['Z', 'XY'],
            'D2': ['XZ', 'YZ'],
            'D2h': ['X', 'Y', 'Z'],
        }

        return generators[self.group]

    @staticmethod
    def get_generators_list() -> list[str]:
        output: list[str] = [f'{Symmetry.GROUPS[0]} (no generators)']
        for group in Symmetry.GROUPS[1:]:
            generators = ' '.join(Symmetry(group).generators)
            output.append(f'{group} ({generators})')

        return output

    def get_all_symmetry_elements(self) -> list[str]:
        elements: list[str] = []
        for r in range(1, len(self.generators) + 1):
            for comb in combinations(self.generators, r):
                counts = Counter(''.join(comb))
                element = ''.join(char for char in counts if counts[char] % 2 == 1)
                elements.append(element)
        return elements

    def get_irrep(self) -> list[str]:
        irreps = {
            'C1': ['A'],
            'Cs': ["A'", "A''"],
            'C2': ['A', 'B'],
            'Ci': ['Ag', 'Au'],
            'C2v': ['A1', 'B1', 'B2', 'A2'],
            'C2h': ['Ag', 'Au', 'Bu', 'Bg'],
            'D2': ['A', 'B3', 'B2', 'B1'],
            'D2h': ['Ag', 'B3u', 'B2u', 'B1g', 'B1u', 'B2g', 'B3g', 'Au'],
        }
        return ['ALL'] + irreps[self.group]

    def get_dipoles(self) -> list[str]:
        dipoles = {
            'C1': ['A', 'A', 'A'],
            'Cs': ["A'", "A'", "A''"],
            'C2': ['B', 'B', 'A'],
            'Ci': ['Au', 'Au', 'Au'],
            'C2v': ['B1', 'B2', 'A1'],
            'C2h': ['Bu', 'Bu', 'Au'],
            'D2': ['B3', 'B2', 'B1'],
            'D2h': ['B3u', 'B2u', 'B1u'],
        }
        return dipoles[self.group]

    def get_mult_table(self) -> list[list[str]]:
        table = {
            'C1': [['A']],
            'Cs': [["A'", "A''"], ["A''", "A'"]],
            'C2': [['A', 'B'], ['B', 'A']],
            'Ci': [['Ag', 'Au'], ['Au', 'Ag']],
            'C2v': [
                ['A1', 'B1', 'B2', 'A2'],
                ['B1', 'A1', 'A2', 'B2'],
                ['B2', 'A2', 'A1', 'B1'],
                ['A2', 'B2', 'B1', 'A1'],
            ],
            'C2h': [
                ['Ag', 'Au', 'Bu', 'Bg'],
                ['Au', 'Ag', 'Bg', 'Bu'],
                ['Bu', 'Bg', 'Ag', 'Au'],
                ['Bg', 'Bu', 'Au', 'Ag'],
            ],
            'D2': [['A', 'B3', 'B2', 'B1'], ['B3', 'A', 'B1', 'B2'], ['B2', 'B1', 'A', 'B3'], ['B1', 'B2', 'B3']],
            'D2h': [
                ['Ag', 'B3u', 'B2u', 'B1g', 'B1u', 'B2g', 'B3u', 'Au'],
                ['B3u', 'Ag', 'B1g', 'B2u', 'B2g', 'B1u', 'Au', 'B3g'],
                ['B2u', 'B1g', 'Ag', 'B3u', 'B3g', 'Au', 'B1u', 'B2g'],
                ['B1g', 'B2u', 'B3u', 'Ag', 'Au', 'B3g', 'B2g', 'B1u'],
                ['B1u', 'B2g', 'B3g', 'Au', 'Ag', 'B3u', 'B2u', 'B1g'],
                ['B2g', 'B1u', 'Au', 'B3g', 'B3u', 'Ag', 'B1g', 'B2u'],
                ['B3g', 'Au', 'B1u', 'B2g', 'B2u', 'B1g', 'Ag', 'B3u'],
                ['Au', 'B3g', 'B2g', 'B1u', 'B1g', 'B2u', 'B3u', 'Ag'],
            ],
        }
        return table[self.group]

    def mult(self, i_irrep: str, j_irrep: str) -> str:
        i_ind = self.irrep.index(i_irrep) - 1
        j_ind = self.irrep.index(j_irrep) - 1
        return self.mult_table[i_ind][j_ind]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Symmetry):
            return self.group == other.group
        return False
