"""Time-independent notebook wiring structural, scattering, and PAD pages."""

import logging
import re
from tkinter import ttk
from typing import TYPE_CHECKING, cast

import numpy as np

from astra_gui.utils.notebook_module import Notebook

from .notebook_state import CapStrengths, TimeIndependentState
from .pad import Pad
from .scatt_states import ScattStates
from .structural import Structural
from .ti_notebook_page_module import TiNotebookPage

if TYPE_CHECKING:
    from astra_gui.app import Astra
    from astra_gui.close_coupling.create_cc_notebook import CreateCcNotebook

logger = logging.getLogger(__name__)


class TimeIndependentNotebook(Notebook[TiNotebookPage]):
    """Coordinate the time-independent calculation pages."""

    def __init__(self, parent: ttk.Frame, controller: 'Astra') -> None:
        """Initialise the notebook and register default pages."""
        super().__init__(parent, controller, 'Run Time Independent Programs')

        self.state: TimeIndependentState = TimeIndependentState()

        self.reset()

        self.add_pages([Structural, ScattStates, Pad])

    def erase_cc_data(self) -> None:
        """Clear stored close-coupling data from every page."""
        for notebook_page in self.pages:
            notebook_page.erase_cc_data()

    def show_cap_radii(self, radii: list[str]) -> None:
        """Propagate CAP radii values to each child page."""
        self.state['cap_radii'] = radii
        for notebook_page in self.pages:
            notebook_page.show_cap_radii(radii)

    def get_cap_strengths(self, group_syms: bool = True, return_float: bool = False) -> CapStrengths:
        """Read CAP strengths from disk and optionally group them by symmetry.

        Returns
        -------
        CapStrengths
            CAP strengths grouped by symmetry label.
        """
        cap_strengths: CapStrengths = {}

        state_syms = self.pages[0].get_computed_syms()
        if not state_syms:
            return cast(CapStrengths, {})

        mult = state_syms[0][0]

        file_pattern = r'zH_Fullc_Fullc_eval*-*'
        file_pattern_regex = re.compile(r'zH_Fullc_Fullc_eval([-+]?\d*\.\d+D[-+]?\d+)-([-+]?\d*\.\d+D[-+]?\d+)')

        assert self.controller.running_directory is not None, 'Running directory is not set.'
        for state_sym in state_syms:
            base_path = self.controller.running_directory / f'store/CloseCoupling/{state_sym}/Full/'

            paths = []
            if self.controller.ssh_client:
                stdout, _, exit_code = self.controller.ssh_client.run_remote_command(
                    f"find '{base_path}' -name {file_pattern} -print",
                )
                if exit_code:
                    logger.warning('Error finding computed cap strengths: %d', exit_code)
                if stdout:
                    paths = stdout.splitlines()
            else:
                paths = list(base_path.glob(file_pattern))

            if paths:
                for path in paths:
                    str_path = str(path).strip()
                    if any(s in str_path for s in ['MinImag', 'MaxImag', 'MinReal', 'MaxReal', 'cropped']):
                        continue

                    match = file_pattern_regex.search(str_path)
                    if match:
                        strengths: list[str | float] = []
                        for group in match.groups():
                            strength = group.strip().replace('D', 'e')
                            strength = float(strength)
                            if not return_float:
                                if strength == 0:
                                    strengths.append('0')
                                else:
                                    strengths.append(str(f'{strength:.1e}'))
                            else:
                                strengths.append(strength)
                        cap_strengths.setdefault(state_sym, []).append(strengths)

        if group_syms:
            cap_strengths = self.group_cap_strengths_by_sym(cap_strengths, mult=mult)

        return cap_strengths

    def show_cap_strengths(self) -> None:
        """Broadcast CAP strengths to every notebook page."""
        cap_strengths = self.get_cap_strengths()
        self.state['cap_strengths'] = cap_strengths
        for notebook_page in self.pages:
            notebook_page.show_cap_strengths(cap_strengths)

    @staticmethod
    def group_cap_strengths_by_sym(cap_strengths: CapStrengths, mult: str) -> CapStrengths:
        """Group CAP strengths by symmetry, consolidating shared values.

        Returns
        -------
        CapStrengths
            CAP strengths reorganised by symmetry, including shared entries.
        """
        new_cap_strengths: CapStrengths = {}

        all_strengths: list[list[str | float]] = []
        other_sym_strengths: CapStrengths = {}

        for i_sym, i_strengths_list in cap_strengths.items():
            for i_strengths in i_strengths_list:
                shared_across_all = True
                for j_sym, j_strengths_list in cap_strengths.items():
                    if i_sym == j_sym:
                        continue

                    if i_strengths not in j_strengths_list:
                        shared_across_all = False
                        other_list = other_sym_strengths.setdefault(i_sym, [])
                        if i_strengths not in other_list:
                            other_list.append(i_strengths)

                if shared_across_all and i_strengths not in all_strengths:
                    all_strengths.append(i_strengths)

        new_cap_strengths[f'{mult}ALL'] = all_strengths
        return new_cap_strengths | other_sym_strengths

    def show_cc_data(self, cc_syms: list[str], target_states_data: np.ndarray, open_channels: list[bool]) -> None:
        """Update all pages with the latest close-coupling target states."""
        TiNotebookPage.cc_syms = cc_syms
        computed_syms = self.pages[0].get_computed_syms()
        TiNotebookPage.computed_syms = computed_syms

        self.state['cc_syms'] = cc_syms
        self.state['computed_syms'] = computed_syms
        self.state['target_states_data'] = target_states_data
        self.state['open_channels'] = open_channels

        for notebook_page in self.pages:
            notebook_page.show_cc_data(target_states_data, open_channels)

    def reset(self) -> None:
        """Refresh cached close-coupling data and reset each page."""
        create_cc_notebook = cast('CreateCcNotebook', self.controller.notebooks[1])
        cc_syms = cast(list[str], create_cc_notebook.cc_data['total_syms'])
        TiNotebookPage.cc_syms = cc_syms

        self.state.clear()
        self.state['cap_strengths'] = cast(CapStrengths, {})
        self.state['cap_radii'] = []
        self.state['cc_syms'] = cc_syms
        self.state['computed_syms'] = []

        self.erase()
