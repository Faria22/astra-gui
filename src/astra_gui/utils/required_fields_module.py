"""Test file."""

import logging
from dataclasses import dataclass
from dataclasses import fields as dc_fields
from typing import get_type_hints

from astra_gui.utils.notebook_module import NotebookPage
from astra_gui.utils.popup_module import invalid_input_popup, required_field_popup

logger = logging.getLogger(__name__)


@dataclass
class RequiredFields:
    """Class to hold required fields and their corresponding widgets.

    Widgets should be named as <field_name>_widget.
    """

    @staticmethod
    def is_valid(val: str, expected_type: type) -> bool:
        """Check if the value is valid for the given type.

        Parameters
        ----------
            val (str): The value to check.
            t (type): The type to check against.

        Returns
        -------
            bool: True if the value is valid for the type, False otherwise.
        """
        try:
            if expected_type is int and str(int(val)) != val:
                return False
            expected_type(val)
        except ValueError:
            return False

        return True

    def check_fields(self) -> bool:
        """Validate required widgets and return their parsed values when successful.

        Returns
        -------
            bool: True if all required fields are valid, False otherwise.
        """
        hints = get_type_hints(self.__class__)
        for f in dc_fields(self):
            field_name = f.name
            logger.debug('Checking required field: %s', field_name)
            if 'widget' in field_name:
                continue
            expected_type = hints.get(field_name, str)
            widget = getattr(self, f'{field_name}_widget')

            val = NotebookPage.get_text_from_widget(widget)

            if not val:
                required_field_popup(field_name)
                return False

            if not self.is_valid(val, expected_type):
                type_str = 'integer' if expected_type is int else 'float' if expected_type is float else 'string'
                invalid_input_popup(f'{field_name} must be a {type_str} value.')
                return False

            setattr(self, field_name, expected_type(val))

        return True
