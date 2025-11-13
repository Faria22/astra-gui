"""Reusable table widget with optional combobox support."""

import tkinter as tk
from functools import partial
from itertools import zip_longest
from tkinter import ttk

import numpy as np

from .scrollable_module import ScrollableFrame


class Table:
    """Render a tabular collection of entry/combobox widgets inside a frame."""

    # Create a type so we can check for ttk.Entry or ttk.Combobox
    ENTRY_OR_COMBO = ttk.Entry | ttk.Combobox

    def __init__(
        self,
        frame: ttk.Frame,
        col_labels: list[str],
        col_types: list[str] | str = 'entry',
        combobox_values_list: list[list[str]] | None = None,
        default_values: list[str] | None = None,
        start_row: int = 0,
        start_col: int = 0,
        width: int = 10,
        fixed_length: bool = False,
        min_length: int = 1,
        scrollable: bool = True,
        padx: float = 2.5,
        height: int = 300,
    ) -> None:
        """Create a table widget with the provided configuration and defaults."""
        self.frame = frame
        if scrollable:
            scrollable_frame = ScrollableFrame(frame, height=height)
            scrollable_frame.pack(fill=tk.BOTH, expand=True)
            self.frame = scrollable_frame.inner_frame

        self.col_labels = col_labels
        self.num_cols = len(col_labels)

        if isinstance(col_types, str):
            col_types = [col_types] * self.num_cols
        elif len(col_types) != self.num_cols:  # If not a string, then it's a list
            raise ValueError(
                f'Table configuration invalid: expected {self.num_cols} column types, received {len(col_types)}',
            )

        # If not combobox value list was given, make it an empty list
        if not combobox_values_list:
            combobox_values_list = [[] for _ in range(col_types.count('combobox'))]

        # Checks if the number of combobox values is the same as the number of combobox columns
        if col_types.count('combobox') != len(combobox_values_list):
            raise ValueError(
                'Table configuration invalid: combobox value lists do not match combobox columns',
            )

        self.default_values = default_values or []

        self.col_types: list[type[Table.ENTRY_OR_COMBO]] = []
        self.combobox_values_list: list[list[str]] = []
        for col_type in col_types:
            if col_type == 'entry':
                self.col_types.append(ttk.Entry)
            else:
                self.col_types.append(ttk.Combobox)

        self.add_combobox_values_list(combobox_values_list)

        self.start_row = start_row
        self.start_col = start_col
        self.width = width
        self.length = 0

        self.fixed_length = fixed_length
        self.min_length = min_length

        self.padx = padx

        self.create()

    def reset(self) -> None:
        """Clear all entries and recreate the table with initial rows."""
        self.erase()
        self.create()

    def create(self, length: int = 1) -> None:
        """Create headers and row widgets, optionally with a fixed length."""
        for i, label in enumerate(self.col_labels):
            ttk.Label(self.frame, text=label).grid(row=self.start_row, column=self.start_col + i, padx=self.padx)

        self.columns: list[list[Table.ENTRY_OR_COMBO]] = [[] for _ in range(self.num_cols)]
        self.remove_button_list: list[ttk.Button] = []

        self.add_button = ttk.Button(self.frame, text='+', width=2, command=self.add_line)

        for _ in range(length):
            self.add_line()

        self.grid()

    def add_line(self) -> None:
        """Add a single line from the table and prints the new version on the screen."""
        self.move_widgets_down()

        for column, col_type, combobox_values, default_value in zip_longest(
            self.columns,
            self.col_types,
            self.combobox_values_list,
            self.default_values,
        ):
            widget = col_type(self.frame, width=self.width)
            if combobox_values:
                widget['values'] = combobox_values

            if default_value:
                if isinstance(widget, ttk.Entry):
                    widget.insert('0', default_value)
                else:
                    widget.set(default_value)

            column.append(widget)

        self.remove_button_list.append(
            ttk.Button(self.frame, text='-', width=2, command=partial(self.remove_line, self.length)),
        )

        self.length += 1

        self.grid()

    def move_widgets_down(self) -> None:
        """If there are any widgets below the table (in the same frame), it will move it down to create space."""
        for widget in self.frame.grid_slaves():
            row = int(widget.grid_info()['row'])
            col = int(widget.grid_info()['column'])
            if row > self.length + self.start_row + 1:
                widget.grid(row=row + 1, column=col)

    def remove_line(self, ind: int) -> None:
        """Remove a single line from the table and prints the new version on the screen."""
        self.length -= 1
        for col in range(self.num_cols):
            self.columns[col].pop(ind).destroy()
            # Moves all the remaining cells up
            for row in range(ind, self.length):
                widget = self.columns[col][row]
                widget.grid(row=self.start_row + row + 1, column=self.start_col + col, padx=self.padx)

        self.remove_button_list.pop().destroy()

        if self.min_length == self.length:
            for col in range(self.length):
                self.remove_button_list[col].grid_forget()

    def grid(self) -> None:
        """Print the whole table on the screen."""
        for row in range(self.length):
            for col in range(self.num_cols):
                widget = self.columns[col][row]
                if widget.winfo_manager() != 'grid':
                    widget.grid(row=self.start_row + row + 1, column=self.start_col + col, padx=self.padx)

                if not self.fixed_length and self.min_length != self.length:
                    remove_button = self.remove_button_list[row]
                    if remove_button.winfo_manager() != 'grid':
                        remove_button.grid(
                            row=self.start_row + row + 1,
                            column=self.start_col + self.num_cols,
                            padx=self.padx,
                        )

        if not self.fixed_length:
            self.add_button.grid(row=self.start_row + self.length + 1, column=self.start_col + self.num_cols, pady=5)

    def erase(self) -> None:
        """Remove all the data and lines from the table, freeing all the resources used with it."""
        for i in range(self.length):
            for j in range(self.num_cols):
                self.columns[j][i].destroy()
            self.remove_button_list[i].destroy()

        self.add_button.destroy()
        self.length = 0

    def get(self) -> np.ndarray:
        """Return the current table values as a 2D NumPy array.

        Returns
        -------
        np.ndarray
            Array of shape ``(num_columns, num_rows)`` containing string values.
        """
        data = np.empty((self.num_cols, self.length), dtype=object)
        for i in range(self.num_cols):
            for j in range(self.length):
                data[i, j] = self.columns[i][j].get()
        return data.astype(str)

    def put(self, data: np.ndarray) -> None:
        """Populate the table with the provided data array.

        Parameters
        ----------
        data: np.ndarray
            2D array of strings shaped ``(num_columns, num_rows)``.
        """
        self.erase()

        length = len(data[0])
        self.create(length)

        for i, column in enumerate(data):
            for j, cell in enumerate(column):
                self.columns[i][j].delete(0, tk.END)
                self.columns[i][j].insert(0, cell)

    def add_combobox_values_list(self, combobox_values_list: list[list[str]]) -> None:
        """Assign value lists to combobox columns, defaulting entries to empty lists."""
        self.combobox_values_list = []

        for col_type in self.col_types:
            if col_type is ttk.Entry:
                self.combobox_values_list.append([])
            else:
                self.combobox_values_list.append(combobox_values_list.pop(0))
