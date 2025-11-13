"""Test file."""

from tkinter import ttk


class RequiredFields:
    """Class to hold required fields and their corresponding widgets."""

    def __init__(self, fields: list[str], widgets: list[ttk.Entry | ttk.Combobox], types: list[type]) -> None:
        self.fields = fields
        self.widgets = widgets
        self.types = types

    def check_fields(self) -> None:
        """Check if all required fields are filled and valid."""
        raise NotImplementedError('This method is not implemented yet.')

    def __getitem__(self, key: str) -> object:
        """Get the value of a field by its name.

        Parameters
        ----------
            key (str): The name of the field.

        Returns
        -------
            object: The value of the field, cast to the appropriate type.
        """
        idx = self.fields.index(key)
        return self.types[idx](self.widgets[idx].get())
