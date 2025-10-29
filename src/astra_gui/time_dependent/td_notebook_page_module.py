import logging
from typing import TYPE_CHECKING

from notebook_module import NotebookPage

if TYPE_CHECKING:
    from .time_dependent_notebook import TimeDependentNotebook

logger = logging.getLogger(__name__)


class TdNotebookPage(NotebookPage['TimeDependentNotebook']):
    def __init__(self, notebook: 'TimeDependentNotebook', label: str = '') -> None:
        super().__init__(notebook, label)
