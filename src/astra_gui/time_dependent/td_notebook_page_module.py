"""Common base class for pages in the time-dependent notebook."""

import logging
from typing import TYPE_CHECKING

from astra_gui.utils.notebook_module import NotebookPage

if TYPE_CHECKING:
    from .time_dependent_notebook import TimeDependentNotebook

logger = logging.getLogger(__name__)


class TdNotebookPage(NotebookPage['TimeDependentNotebook']):
    """Provide shared behaviour for time-dependent notebook pages."""

    def __init__(self, notebook: 'TimeDependentNotebook', label: str = '') -> None:
        """Initialise the base page with the provided label."""
        super().__init__(notebook, label)
