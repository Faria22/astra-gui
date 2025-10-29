from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING

from utils.notebook_module import NotebookPage

if TYPE_CHECKING:
    from .create_cc_notebook import CreateCcNotebook


class CcNotebookPage(NotebookPage['CreateCcNotebook'], ABC):
    SCRIPT_COMMANDS: list[str]
    MOLDEN_FILE = Path('QC/molden.inp')
    SCRIPT_FILE = Path('run_astra_setup.sh')
    ASTRA_FILE = Path('ASTRA.INP')

    def __init__(
        self,
        notebook: 'CreateCcNotebook',
        label: str = '',
        two_screens: bool = False,
    ) -> None:
        super().__init__(notebook, label, two_screens)

    def run_astra_setup(self, command: str, name: str) -> None:
        if not self.path_exists(self.ASTRA_FILE):
            self.save_file(self.ASTRA_FILE, {'int_library': 'HybridIntegrals'})

        self.save_script(
            self.SCRIPT_FILE,
            {'run_astra_command': command},
            name,
            update_statusbar=False,
            source_file=self.SCRIPT_FILE,
        )
        self.run_script(self.SCRIPT_FILE, name, self.SCRIPT_COMMANDS)

    def left_screen_def(self) -> None: ...

    def right_screen_def(self) -> None: ...
