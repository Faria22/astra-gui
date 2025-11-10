"""Regression tests covering Lucia target-state serialisation."""

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import numpy as np

# Lucia depends on the optional moulden visualiser; provide a lightweight stub.
stub_module = ModuleType('moldenViz')
cast(Any, stub_module).Plotter = None
sys.modules.setdefault('moldenViz', stub_module)

try:
    from astra_gui.close_coupling.lucia import Lucia
except ModuleNotFoundError:
    SRC_PATH = Path(__file__).resolve().parents[1] / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from astra_gui.close_coupling.lucia import Lucia


def test_get_states_data_serialises_numeric_fields() -> None:
    """Numeric symmetry codes should be coerced to strings during save."""

    class DummyTable:
        def __init__(self, data: np.ndarray) -> None:
            self._data = data

        def get(self) -> np.ndarray:
            return self._data

    lucia = Lucia.__new__(Lucia)
    lucia.sym = cast(Any, SimpleNamespace(irrep=['ALL', 'A1']))
    lucia.notebook = cast(Any, SimpleNamespace(lucia_data={}))
    lucia.states_table = cast(
        Any,
        DummyTable(
            np.array(
                [
                    ['A1'],
                    [1],
                    [1],
                ],
                dtype=object,
            ),
        ),
    )
    lucia.unpack_all_sym = Lucia.unpack_all_sym.__get__(lucia, Lucia)

    _, serialized = lucia.get_states_data()

    assert serialized == '1\n1 1 1'
