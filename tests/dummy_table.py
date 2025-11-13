"""Reusable stub that mimics the interface Lucia expects from Table."""

from typing import Any, cast

import numpy as np

from astra_gui.utils.table_module import Table


class DummyEntry:
    """Minimal entry widget replacement storing text without GUI state."""

    def __init__(self) -> None:
        self.value = ''

    def delete(self, *_: Any) -> None:
        """Reset the stored value."""
        self.value = ''

    def insert(self, _: Any, value: Any) -> None:
        """Store the provided value as text."""
        self.value = str(value)

    def get(self) -> str:
        """Return the currently stored text.

        Returns
        -------
        str
            The outstanding value stored in this dummy entry.
        """
        return self.value


class DummyTable:
    """Lightweight Table replacement for tests that exercises :func:`Table.put`."""

    def __init__(self, num_cols: int) -> None:
        self.num_cols = num_cols
        self.columns: list[list[DummyEntry]] = []
        self.length = 0

    def erase(self) -> None:
        """Clear any rows previously stored."""
        self.columns = [[] for _ in range(self.num_cols)]
        self.length = 0

    def create(self, length: int = 1) -> None:
        """Allocate the requested number of columns."""
        self.length = length
        self.columns = [
            [DummyEntry() for _ in range(length)]
            for _ in range(self.num_cols)
        ]

    def get(self) -> np.ndarray:
        """Gather the current table snapshot as an array of strings.

        Returns
        -------
        np.ndarray
            Table contents shaped ``(num_columns, num_rows)`` containing strings.
        """
        data = np.empty((self.num_cols, self.length), dtype=object)
        for i in range(self.num_cols):
            for j in range(self.length):
                data[i, j] = self.columns[i][j].get()
        return data.astype(str)

    def put(self, data: np.ndarray) -> None:
        """Populate the stub with the same logic used by :class:`Table`."""
        Table.put(cast(Table, self), data)
