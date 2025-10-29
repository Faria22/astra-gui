import logging
import re
import tkinter as tk
from abc import ABC, abstractmethod
from pathlib import Path
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING, Any, cast, overload

import numpy as np
from utils.font_module import bold_font
from utils.notebook_module import NotebookPage
from utils.popup_module import invalid_input_popup, warning_popup
from utils.table_module import Table

from .td_notebook_page_module import TdNotebookPage

if TYPE_CHECKING:
    from .time_dependent_notebook import TimeDependentNotebook

logger = logging.getLogger(__name__)


class Pulse:
    PULSE_SHAPES = ['Gaussian', 'Cosine Squared']

    def __init__(
        self,
        shape: str,
        name: str,
        time: float,
        frequency: float,
        fwhm: float,
        cep: float,
        intensity: float,
        theta: float,
        phi: float,
    ) -> None:
        if shape not in self.PULSE_SHAPES:
            invalid_input_popup(
                f'Invalid pulse shape: {shape} for {name}. Valid shapes are: {", ".join(self.PULSE_SHAPES)}',
            )
            return

        self.shape = shape[0]

        self.name = name
        self.time = time
        self.freq = frequency
        self.fwhm = fwhm
        self.cep = cep
        self.intensity = intensity
        self.theta = theta
        self.phi = phi

        self.good_parameters = False
        self.check_attributes()

    def check_attributes(self) -> None:
        attributes = {
            'central time': 'time',
            'central frequency': 'freq',
            'FWHM': 'fwhm',
            'CEP': 'cep',
            'intensity': 'intensity',
            'theta': 'theta',
            'phi': 'phi',
        }

        for label, attr in attributes.items():
            value = getattr(self, attr)
            if value is None:
                invalid_input_popup(f'Missing value for {label} for {self.name}.')
                return
            try:
                setattr(self, attr, float(value))
            except ValueError:
                warning_popup(
                    f'Invalid value for {label}, should be a real number for {self.name}.',
                )
                return

        self.good_parameters = True

    def pulse_string(self) -> str:
        return f'[{self.name}]{{{self.parameter_string()};}}'

    def parameter_string(self) -> str:
        return f'({self.shape} {self.time} {self.freq} {self.fwhm} {self.cep} {self.intensity} {self.theta} {self.phi})'

    @overload
    def eval_envelope(self, t: float) -> float: ...
    @overload
    def eval_envelope(self, t: np.ndarray) -> np.ndarray: ...
    def eval_envelope(self, t: float | np.ndarray) -> float | np.ndarray:
        if self.shape == 'G':
            return np.exp(-np.log(2) * (self.freq * (t - self.time) / (np.pi * self.fwhm)) ** 2)

        argument = self.freq * (t - self.time) / (4.0 * self.fwhm)

        return np.where(np.abs(argument) >= np.pi / 2.0, 0, np.cos(argument) ** 2)

    @overload
    def eval_pulse(self, t: float) -> float: ...
    @overload
    def eval_pulse(self, t: np.ndarray) -> np.ndarray: ...

    def eval_pulse(self, t: float | np.ndarray) -> float | np.ndarray:
        oscilation_funtion = np.cos(self.freq * (t - self.time) + self.cep)
        c_to_au = 137.03599911
        a0 = c_to_au / 18.73 / self.freq * np.sqrt(10 * self.intensity)

        return a0 * self.eval_envelope(t) * oscilation_funtion

    def get_zero_envelope_time(self) -> float:
        if self.shape == 'G':
            threshold = 1e-5
            return np.sqrt(-np.log2(threshold)) * self.fwhm * np.pi / self.freq

        return np.pi * 4.0 * self.fwhm / self.freq / 2

    def get_initial_and_final_times(self) -> tuple[float, float]:
        dt = self.get_zero_envelope_time()
        return self.time - dt, self.time + dt

    def tabulate(self, initial_time: float, final_time: float, dt: float) -> str:
        times = np.arange(initial_time, final_time + dt, dt)
        pulse_values = self.eval_pulse(times)

        lines = [f'{t} {pulse_value}' for t, pulse_value in zip(times, pulse_values)]

        return '\n'.join(lines)


class Pulses:
    def __init__(self, name: str, pulses: list[Pulse]) -> None:
        self.name = name
        self.pulses = pulses

    def pulses_string(self) -> str:
        return f'[{self.name}]{{{";".join([pulse.name for pulse in self.pulses])};}}'

    def get_initial_and_final_times(self) -> tuple[float, float]:
        min_time = np.inf
        max_time = -np.inf

        for pulse in self.pulses:
            pulse_min_time, pulse_max_time = pulse.get_initial_and_final_times()
            min_time = min(min_time, pulse_min_time)
            max_time = max(max_time, pulse_max_time)

        return min_time, max_time


class PumpProbePulses:
    def __init__(self, pump: Pulses, probe: Pulses, time_delays: np.ndarray) -> None:
        self.pump = pump
        self.probe = probe
        self.time_delays = time_delays

    def probe_string(self, time_delay: float) -> str:
        probe_parameters = []
        for probe_pulse in self.probe.pulses:
            probe_pulse.time = time_delay
            probe_parameters.append(probe_pulse.parameter_string())

        return ';'.join(probe_parameters)

    def pump_probe_string(self) -> str:
        lines = [
            f'[pump_probe_{time_delay}]{{{self.pump.name}; {self.probe_string(time_delay)};}}'
            for time_delay in self.time_delays
        ]

        return '\n'.join(lines)

    def execute_string(self) -> str:
        return f'EXECUTE{{{self.pump.name};' + ';'.join([f'pump_probe_{td}' for td in self.time_delays]) + ';}'

    def get_initial_and_final_times(self) -> tuple[float, float]:
        min_time, max_time = self.pump.get_initial_and_final_times()

        for time_delay in self.time_delays[[0, -1]]:
            for probe_pulse in self.probe.pulses:
                probe_pulse.time = time_delay

            probe_min_time, probe_max_time = self.probe.get_initial_and_final_times()
            min_time = min(min_time, probe_min_time)
            max_time = max(max_time, probe_max_time)

        return min_time, max_time


class PulseParameterFrame(ttk.Frame, ABC):
    PULSE_PARAMETER_COLUMNS = [
        'Central time [au]',
        'Central frequency [au]',
        'FWHM [Periods]',
        'CEP [degrees]',
        'Intensity [PW/cm^2]',
        'Theta [degrees]',
        'Phi [degrees]',
    ]

    # Expected number of parameters in pulse definition:
    # 1. Shape (G/C), 2. Central time, 3. Central frequency, 4. FWHM,
    # 5. CEP, 6. Intensity, 7. Theta, 8. Phi
    EXPECTED_PARAM_COUNT = 1 + len(PULSE_PARAMETER_COLUMNS)

    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent)
        self.hover_widget = NotebookPage.hover_widget
        self.check_field_entries = NotebookPage.check_field_entries

    @abstractmethod
    def save(
        self,
    ) -> tuple[dict[str, str], dict[str, str], Path, Path, dict[str, str]] | None:
        """
        Save the pulse parameters and simulation parameters.

        Returns: One dictionary with the pulse data,
                 one dictionary with the TDSE data,
                 the pulse filename and the TDSE filename,
                 and one dictionary with file name and data for pulse tabulation.
        """
        ...

    @abstractmethod
    def erase(self) -> None:
        pass


class PumpProbeFrame(PulseParameterFrame):
    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent)

        # Pump
        pump_params_frame = ttk.Frame(self)
        pump_params_frame.grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(pump_params_frame, text='Pump', font=bold_font).grid(row=0, column=0)
        ttk.Label(pump_params_frame, text='Shape:').grid(row=1, column=0)

        self.pump_shape_combo = ttk.Combobox(pump_params_frame, width=15, values=Pulse.PULSE_SHAPES, state='readonly')
        self.pump_shape_combo.grid(row=1, column=1)
        self.pump_shape_combo.current(0)

        pump_frame = ttk.Frame(self)
        pump_frame.grid(row=1, column=0, columnspan=10)
        self.pump_table = Table(
            pump_frame,
            self.PULSE_PARAMETER_COLUMNS,
            default_values=['0.0'] + [''] * (len(self.PULSE_PARAMETER_COLUMNS) - 1),
            height=150,
        )

        # Probe
        probe_params_frame = ttk.Frame(self)
        probe_params_frame.grid(row=2, column=0, columnspan=3, sticky='w')
        ttk.Label(probe_params_frame, text='Probe', font=bold_font).grid(row=0, column=0)
        ttk.Label(probe_params_frame, text='Shape:').grid(row=1, column=0)

        self.probe_shape_combo = ttk.Combobox(probe_params_frame, width=15, values=Pulse.PULSE_SHAPES, state='readonly')
        self.probe_shape_combo.current(1)
        self.probe_shape_combo.grid(row=1, column=1)
        probe_frame = ttk.Frame(self)
        probe_frame.grid(row=3, column=0, columnspan=10, sticky='w')
        self.probe_table = Table(probe_frame, self.PULSE_PARAMETER_COLUMNS[1:], height=150)

        # Simulation Parameters
        ttk.Label(self, text='Simulation Parameters', font=bold_font).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky='w',
            pady=(30, 0),
        )
        sim_params_frame = ttk.Frame(self)
        sim_params_frame.grid(row=5, column=0, columnspan=3, sticky='w')

        assumption_text = 'Assumes the APT is centered at t = 0.'

        # Min delta t
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Minimum time-delay [au]:',
            hover_text=assumption_text,
        ).grid(row=0, column=0)
        self.min_tau = ttk.Entry(sim_params_frame, width=10)
        self.min_tau.grid(row=0, column=1)

        # Max delta t
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Maximum time-delay [au]:',
            hover_text=assumption_text,
        ).grid(row=1, column=0)
        self.max_tau = ttk.Entry(sim_params_frame, width=10)
        self.max_tau.grid(row=1, column=1)

        # Time delay spacing
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Time-delay spacing [au]:',
            hover_text=assumption_text,
        ).grid(row=2, column=0)
        self.delta_tau = ttk.Entry(sim_params_frame, width=10)
        self.delta_tau.grid(row=2, column=1)

        # Simulation label
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Simulation label:',
            hover_text='Label used to mark the input and output files.',
        ).grid(row=3, column=0)
        self.sim_label = ttk.Entry(sim_params_frame, width=10)
        self.sim_label.grid(row=3, column=1)

    def save(
        self,
    ) -> tuple[dict[str, str], dict[str, str], Path, Path, dict[str, str]] | None:
        required_fields = [
            ('Minimum time-delay', self.min_tau, float),
            ('Maximum time-delay', self.max_tau, float),
            ('Time-delay spacing', self.delta_tau, float),
            ('Simulation label', self.sim_label, str),
        ]

        if not (required_fields := self.check_field_entries(required_fields)):
            return None

        min_tau = cast(float, required_fields['Minimum time-delay'])
        max_tau = cast(float, required_fields['Maximum time-delay'])
        delta_tau = cast(float, required_fields['Time-delay spacing'])
        sim_label = required_fields['Simulation label']

        pump_data = self.pump_table.get().T
        probe_data = self.probe_table.get().T

        if np.any(pump_data == ''):  # noqa: PLC1901
            invalid_input_popup('Missing attributes for pump pulse(s).')
            return None

        if np.any(probe_data == ''):  # noqa: PLC1901
            invalid_input_popup('Missing attributes for probe pulse(s).')
            return None

        pump = Pulses(
            'pump_train',
            [
                Pulse(
                    self.pump_shape_combo.get(),
                    f'pump_{n}',
                    *single_pump_data,
                )
                for n, single_pump_data in enumerate(pump_data)
            ],
        )

        probe = Pulses(
            'probe_train',
            [
                Pulse(
                    self.probe_shape_combo.get(),
                    f'probe_{n}',
                    0,
                    *single_probe_data,
                )
                for n, single_probe_data in enumerate(probe_data)
            ],
        )

        pump_probe_pulses = PumpProbePulses(pump, probe, np.arange(min_tau, max_tau + delta_tau, delta_tau))

        pulse_data = {
            'type': 'pump/probe',
            'pump_pulses': '\n'.join([pulse.pulse_string() for pulse in pump.pulses]),
            'pump_train': pump.pulses_string(),
            'pump_probe_pulses': pump_probe_pulses.pump_probe_string(),
            'execute': pump_probe_pulses.execute_string(),
        }

        pulse_filename = f'{PulsePage.BASE_PULSE_FILE}_{sim_label}'

        intial_time, final_time = pump_probe_pulses.get_initial_and_final_times()

        # Tabulates the pump and probe pulses
        pulse_tabulation = {}
        for pump_pulse in pump.pulses:
            pulse_tabulation[pump_pulse.name] = pump_pulse.tabulate(
                intial_time,
                final_time,
                PulsePage.TIME_STEP,
            )

        for probe_pulse in probe.pulses:
            probe_pulse.time = 0
            pulse_tabulation[probe_pulse.name] = probe_pulse.tabulate(
                intial_time,
                final_time,
                PulsePage.TIME_STEP,
            )

        ######################################
        tdse_data = {
            'pulse_filename': pulse_filename,
            'structure_dir': f'TDSE_input_files_{sim_label}',
            'initial_time': intial_time - PulsePage.DELTA_START_TIME,
            'final_time': final_time + PulsePage.DELTA_END_TIME,
            'final_pulse_time': final_time,
            'time_step': PulsePage.TIME_STEP,
            'save_time_step': PulsePage.SAVE_TIME_STEP,
            'label': sim_label,
        }

        tdse_filename = f'{PulsePage.BASE_TDSE_FILE}_{sim_label}'

        return (
            pulse_data,
            tdse_data,
            Path(pulse_filename),
            Path(tdse_filename),
            pulse_tabulation,
        )

    def load(self, pulse_lines: list[str], sim_label: str = '') -> None:
        """
        Load pump-probe pulse parameters from a saved pump-probe pulse file.

        Args:
            pulse_lines: Lines from the pulse file with comments removed
            sim_label: The simulation label extracted from the filename
        """
        # Extract pump pulse data
        pump_data = self._extract_pump_data(pulse_lines)
        probe_data, time_delays = self._extract_probe_data(pulse_lines)

        # Check if required data exists, show popup and return if missing
        if pump_data is None or probe_data is None or not time_delays:
            warning_popup('Invalid pump-probe pulse file: Missing required pulse data.')
            return

        self.pump_table.put(pump_data)
        self.probe_table.put(probe_data)
        self._set_time_delay_parameters(time_delays)

        # Set simulation label
        self.sim_label.delete(0, tk.END)
        self.sim_label.insert(0, sim_label)

    def _extract_pump_data(self, pulse_lines: list[str]) -> np.ndarray | None:
        """Extract pump pulse parameters from pulse lines."""
        pump_pulse_lines = []

        # Find lines that define individual pump pulses (before pump_train)
        for line in pulse_lines:
            clean_line = line.strip()
            if not clean_line:
                continue

            # Look for pump pulse definitions like [pump_0]{(G 0.0 10.0 10.0 0.0 1.0 0.0 0.0);}
            if re.match(r'\[pump_\d+\]', clean_line):
                pump_pulse_lines.append(clean_line)

        if not pump_pulse_lines:
            return None

        # Extract parameters from pump pulse lines
        pump_data = []
        pump_shape = None

        for line in pump_pulse_lines:
            # Extract pulse parameters from inside parentheses
            match = re.search(r'\((.*?)\)', line)
            if match:
                params = match.group(1).split()
                if len(params) != self.EXPECTED_PARAM_COUNT:
                    warning_popup(f'Pump pulse has {len(params)} parameters but expected {self.EXPECTED_PARAM_COUNT}.')
                    continue

                shape = params[0]
                numeric_params = [float(p) for p in params[1 : self.EXPECTED_PARAM_COUNT]]
                pump_data.append(numeric_params)

                # Set pump shape from first pulse (should be consistent)
                if pump_shape is None:
                    full_shape = 'Gaussian' if shape == 'G' else 'Cosine Squared'
                    shape_index = Pulse.PULSE_SHAPES.index(full_shape)
                    self.pump_shape_combo.current(shape_index)
                    pump_shape = shape
                elif shape != pump_shape:
                    warning_popup('Inconsistent pump pulse shapes found.')
                    return None

        return np.array(pump_data).T if pump_data else None

    def _extract_probe_data(self, pulse_lines: list[str]) -> tuple[np.ndarray | None, list[float]]:
        """Extract probe pulse parameters and time delays from pulse lines."""
        pump_probe_lines = []

        # Find pump_probe lines like [pump_probe_0.1]{pump_train; (C 0.1 5.0 5.0 90.0 0.5 45.0 90.0);}
        for line in pulse_lines:
            clean_line = line.strip()
            if not clean_line:
                continue

            if re.match(r'\[pump_probe_', clean_line):
                pump_probe_lines.append(clean_line)

        if not pump_probe_lines:
            return None, []

        probe_data = set()
        time_delays = []
        probe_shape = None

        for line in pump_probe_lines:
            # Extract time delay from pump_probe name
            delay_match = re.search(r'\[pump_probe_([-+]?\d*\.?\d+)\]', line)
            if delay_match:
                time_delays.append(float(delay_match.group(1)))

            # Extract probe pulse parameters (after the semicolon)
            # Look for the probe pulse parameters in parentheses after pump_train;
            parts = line.split(';')
            for part in parts:
                if '(' in part and ')' in part:
                    match = re.search(r'\((.*?)\)', part)
                    if match:
                        params = match.group(1).split()
                        if len(params) != self.EXPECTED_PARAM_COUNT:
                            warning_popup(
                                f'Probe pulse has {len(params)} parameters but expected {self.EXPECTED_PARAM_COUNT}.',
                            )
                            return None, []

                        shape = params[0]
                        # For probe, skip the time parameter (index 1) since it varies
                        numeric_params = tuple(
                            float(p) for p in params[2 : self.EXPECTED_PARAM_COUNT]
                        )  # Skip shape and time
                        probe_data.add(numeric_params)

                        # Set probe shape from first pulse (should be consistent)
                        if probe_shape is None:
                            full_shape = 'Gaussian' if shape == 'G' else 'Cosine Squared'
                            shape_index = Pulse.PULSE_SHAPES.index(full_shape)
                            self.probe_shape_combo.current(shape_index)
                            probe_shape = shape
                        elif shape != probe_shape:
                            warning_popup('Inconsistent probe pulse shapes found.')
                            return None, []

        if probe_data:
            return np.array(list(probe_data)).T, time_delays

        return None, time_delays

    def _set_time_delay_parameters(self, time_delays: list[float]) -> None:
        """Set time delay parameters based on extracted time delays."""
        if not time_delays:
            return

        time_delays.sort()  # Ensure they're in order
        min_tau = min(time_delays)
        max_tau = max(time_delays)

        # Calculate delta_tau
        if len(time_delays) > 1:
            # Use the smallest non-zero difference between consecutive delays
            deltas = [time_delays[i + 1] - time_delays[i] for i in range(len(time_delays) - 1)]
            delta_tau = min(d for d in deltas if d > 0) if deltas else 1.0
        else:
            delta_tau = 1.0

        # Set the values in the GUI
        self.min_tau.delete(0, tk.END)
        self.min_tau.insert(0, str(min_tau))

        self.max_tau.delete(0, tk.END)
        self.max_tau.insert(0, str(max_tau))

        self.delta_tau.delete(0, tk.END)
        self.delta_tau.insert(0, str(delta_tau))

    def erase(self) -> None:
        self.pump_shape_combo.current(0)
        self.pump_table.reset()

        self.probe_shape_combo.current(1)
        self.probe_table.reset()

        self.min_tau.delete(0, tk.END)
        self.max_tau.delete(0, tk.END)
        self.delta_tau.delete(0, tk.END)
        self.sim_label.delete(0, tk.END)


class CustomPulseFrame(PulseParameterFrame):
    def __init__(self, parent: ttk.Frame) -> None:
        super().__init__(parent)

        ttk.Label(self, text='Pulses', font=bold_font).grid(row=0, column=0)
        pulses_frame = ttk.Frame(self)
        pulses_frame.grid(row=1, column=0, columnspan=10, sticky='w')

        table_columns = ['Shape', *self.PULSE_PARAMETER_COLUMNS]
        table_column_types = ['combobox'] + ['entry'] * len(
            self.PULSE_PARAMETER_COLUMNS,
        )
        default_values = [Pulse.PULSE_SHAPES[0], '0.0']

        self.pulse_table = Table(
            pulses_frame,
            table_columns,
            table_column_types,
            combobox_values_list=[Pulse.PULSE_SHAPES],
            default_values=default_values + [''] * (len(self.PULSE_PARAMETER_COLUMNS) - 2),
            height=150,
        )

        ########################################
        # Simulation Parameters
        ttk.Label(self, text='Simulation Parameters', font=bold_font).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky='w',
            pady=(30, 15),
        )
        sim_params_frame = ttk.Frame(self)
        sim_params_frame.grid(row=3, column=0, columnspan=3, sticky='w')

        # Estimate parameters button
        estimate_params_buttom = ttk.Button(
            self,
            text='Estimate parameters',
            command=self.estimate_simulation_parameters,
        )
        estimate_params_buttom.grid(row=2, column=2, sticky='w', pady=(30, 15))

        # Initial time
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Initial time [au]:',
            hover_text='The initial time for the simulation.u.',
        ).grid(row=0, column=0)
        self.initial_time_entry = ttk.Entry(sim_params_frame)
        self.initial_time_entry.grid(row=0, column=1)

        # Final time
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Final time [au]:',
            hover_text='The final time for the simulation.u.',
        ).grid(row=1, column=0)
        self.final_time_entry = ttk.Entry(sim_params_frame)
        self.final_time_entry.grid(row=1, column=1)

        # Final pulse time
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Final pulse time [au]:',
            hover_text="""The time for which all the pulses can be considered to be over,
                          just free propagation afterwards.""",
        ).grid(row=2, column=0)
        self.final_pulse_time_entry = ttk.Entry(sim_params_frame)
        self.final_pulse_time_entry.grid(row=2, column=1)

        # Time step
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Time step [au]:',
            hover_text='The time step for the numerical time propagation.',
        ).grid(row=3, column=0)
        self.time_step_entry = ttk.Entry(sim_params_frame)
        self.time_step_entry.grid(row=3, column=1)

        # Save time step
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Save time step [au]:',
            hover_text='Time step for which the time-dependent wave function will be saved.',
        ).grid(row=4, column=0)
        self.save_time_step_entry = ttk.Entry(sim_params_frame)
        self.save_time_step_entry.grid(row=4, column=1)

        # Simulation label
        self.hover_widget(
            ttk.Label,
            sim_params_frame,
            text='Simulation label:',
            hover_text='Label used to mark the input and output files.',
        ).grid(row=5, column=0)
        self.sim_label_entry = ttk.Entry(sim_params_frame)
        self.sim_label_entry.grid(row=5, column=1)

    def estimate_simulation_parameters(self) -> None:
        pulse_data = self.pulse_table.get().T

        if np.any(pulse_data == ''):  # noqa: PLC1901
            invalid_input_popup('Missing attributes for pulse(s).')
            return

        pulses = Pulses(
            'pulses',
            [Pulse(pulse_data[0], f'pulse_{n}', *pulse_data[1:]) for n, pulse_data in enumerate(pulse_data)],
        )

        pulse_min_time, pulse_max_time = pulses.get_initial_and_final_times()

        self.erase_simulation_parameters()

        self.initial_time_entry.insert(
            0,
            str(pulse_min_time - PulsePage.DELTA_START_TIME),
        )
        self.final_time_entry.insert(0, str(pulse_max_time + PulsePage.DELTA_END_TIME))
        self.final_pulse_time_entry.insert(0, str(pulse_max_time))
        self.time_step_entry.insert(0, str(PulsePage.TIME_STEP))
        self.save_time_step_entry.insert(0, str(PulsePage.SAVE_TIME_STEP))

    def save(self) -> tuple[dict[str, str], dict[str, str], Path, Path, dict[str, str]] | None:
        pulse_data = self.pulse_table.get().T

        if np.any(pulse_data == ''):  # noqa: PLC1901
            invalid_input_popup('Missing attributes for pulse(s).')
            return None

        pulses = Pulses(
            'pulses',
            [Pulse(pulse_data[0], f'pulse_{n}', *pulse_data[1:]) for n, pulse_data in enumerate(pulse_data)],
        )

        pulse_data = {
            'type': 'custom',
            'pulses': '\n'.join([pulse.pulse_string() for pulse in pulses.pulses]),
            'pulses_train': pulses.pulses_string(),
            'execute': f'EXECUTE{{{pulses.name};}}',
        }

        pulse_filename = f'{PulsePage.BASE_PULSE_FILE}_{self.sim_label_entry.get()}'

        ########################################
        # TDSE
        required_fields = [
            ('Initial time', self.initial_time_entry, float),
            ('Final time', self.final_time_entry, float),
            ('Final pulse time', self.final_pulse_time_entry, float),
            ('Time step', self.time_step_entry, float),
            ('Save time step', self.save_time_step_entry, float),
            ('Simulation label', self.sim_label_entry, str),
        ]

        if not (required_fields := self.check_field_entries(required_fields)):
            return None

        tdse_data = {
            'pulse_filename': pulse_filename,
            'structure_dir': f'TDSE_input_files_{self.sim_label_entry.get()}',
            'initial_time': required_fields['Initial time'],
            'final_time': required_fields['Final time'],
            'final_pulse_time': required_fields['Final pulse time'],
            'time_step': required_fields['Time step'],
            'save_time_step': required_fields['Save time step'],
            'label': required_fields['Simulation label'],
        }

        tdse_filename = f'{PulsePage.BASE_TDSE_FILE}_{self.sim_label_entry.get()}'

        # Tabulates the pulses
        pulse_tabulation = {}
        for pulse in pulses.pulses:
            pulse_tabulation[pulse.name] = pulse.tabulate(
                tdse_data['initial_time'],
                tdse_data['final_time'],
                tdse_data['time_step'],
            )

        return (
            pulse_data,
            tdse_data,
            Path(pulse_filename),
            Path(tdse_filename),
            pulse_tabulation,
        )

    def load(self, pulse_lines: list[str], tdse_lines: list[str], sim_label: str) -> None:
        pulse_strings = [
            match.group(1) for pulse_line in pulse_lines[:-2] for match in re.compile(r'\((.*?)\)').finditer(pulse_line)
        ]

        pulse_data = self.convert_pulse_data(pulse_strings)

        initial_time, final_time, final_pulse_time, time_step, save_time_step = self.extract_tdse_parameters(tdse_lines)

        self.pulse_table.put(pulse_data)
        self.initial_time_entry.insert(0, initial_time)
        self.final_time_entry.insert(0, final_time)
        self.final_pulse_time_entry.insert(0, final_pulse_time)
        self.time_step_entry.insert(0, time_step)
        self.save_time_step_entry.insert(0, save_time_step)
        self.sim_label_entry.insert(0, sim_label)

    @staticmethod
    def extract_tdse_parameters(tdse_lines: list[str]) -> tuple[str, str, str, str, str]:
        def extract_value(line: str) -> str:
            return line.split('=')[1].strip()

        initial_time = final_time = final_pulse_time = time_step = save_time_step = ''
        for line in tdse_lines:
            if 'Initial_Time' in line:
                initial_time = extract_value(line)
            elif 'Final_Time_Pulse' in line:
                final_pulse_time = extract_value(line)
            elif 'Final_Time' in line:
                final_time = extract_value(line)
            elif 'Time_Step' in line:
                time_step = extract_value(line)
            elif 'Save_Time_Interval' in line:
                save_time_step = extract_value(line)

        if not all([
            initial_time,
            final_time,
            final_pulse_time,
            time_step,
            save_time_step,
        ]):
            invalid_input_popup('Missing attributes for TDSE parameters.')
            return '', '', '', '', ''

        return initial_time, final_time, final_pulse_time, time_step, save_time_step

    @staticmethod
    def convert_pulse_data(pulse_strings: list[str]) -> np.ndarray:
        shapes = {shape[0]: shape for shape in Pulse.PULSE_SHAPES}

        pulse_data = []
        for pulse_string in pulse_strings:
            data: list[Any] = pulse_string.split()

            if len(data) != PulseParameterFrame.EXPECTED_PARAM_COUNT:
                warning_popup(
                    f'Pulse has {len(data)} parameters but expected {PulseParameterFrame.EXPECTED_PARAM_COUNT}.',
                )
                return np.array([])

            data[0] = shapes[data[0]]
            data[1:] = [float(value) for value in data[1:]]
            pulse_data.append(data)

        return np.array(pulse_data).T

    def erase_simulation_parameters(self) -> None:
        self.initial_time_entry.delete(0, tk.END)
        self.final_time_entry.delete(0, tk.END)
        self.final_pulse_time_entry.delete(0, tk.END)
        self.time_step_entry.delete(0, tk.END)
        self.save_time_step_entry.delete(0, tk.END)

    def erase(self) -> None:
        self.pulse_table.reset()

        self.erase_simulation_parameters()
        self.sim_label_entry.delete(0, tk.END)


class PulsePage(TdNotebookPage):
    BASE_PULSE_FILE = Path('PULSE.INP')
    BASE_TDSE_FILE = Path('TDSE.INP')
    CUSTOM_PULSE_FILE = Path('PULSE.INP_Custom')
    PUMP_PROBE_FILE = Path('PULSE.INP_Pump_Probe')
    DELTA_START_TIME = 10.0
    DELTA_END_TIME = 60.0
    TIME_STEP = 0.03
    SAVE_TIME_STEP = 1.0

    PUMP_PROBE_LABEL = 'pump-probe'
    CUSTOM_LABEL = 'arbitrary'

    def __init__(self, notebook: 'TimeDependentNotebook') -> None:
        super().__init__(notebook, 'Pulse Parameters')

        self.pump_probe_frame = PumpProbeFrame(self)
        self.custom_pulse_frame = CustomPulseFrame(self)

        ttk.Button(self, text='Load pulse file', command=self.load_files).grid(row=0, column=0, sticky='w', pady=15)

        ttk.Label(self, text='Type of simulation:').grid(row=1, column=0, sticky='w', pady=(0, 15))
        self.sim_type_combo = ttk.Combobox(self, state='readonly', values=['Pump-probe', 'Custom'])
        self.sim_type_combo.current(0)
        self.sim_type_combo.grid(row=1, column=1, sticky='w', pady=(0, 15))
        self.sim_type_combo.bind('<<ComboboxSelected>>', self.show_sim_type_frame)

        self.show_sim_type_frame()

        self.save_button.grid(row=3, column=0, sticky='w', pady=15)

    def show_sim_type_frame(self, _event: tk.Event | None = None) -> None:
        if self.sim_type_combo.get() == 'Pump-probe':
            self.pump_probe_frame.grid(row=2, column=0, columnspan=10, sticky='w')
            self.custom_pulse_frame.grid_forget()
        else:
            self.custom_pulse_frame.grid(row=2, column=0, columnspan=10, sticky='w')
            self.pump_probe_frame.grid_forget()

    def erase(self) -> None:
        self.sim_type_combo.current(0)
        self.pump_probe_frame.erase()
        self.custom_pulse_frame.erase()

    def load(self) -> None: ...

    def load_files(self) -> None:
        title = 'Select pulse file'
        if self.ssh_client:
            pulse_file = self.ssh_client.browse_remote(
                self.controller.running_directory,
                title=title,
                dirs=False,
                files=True,
            )
        else:
            pulse_file = filedialog.askopenfilename(title=title, initialdir=self.controller.running_directory)

        if not pulse_file:
            return

        pulse_file_path = Path(pulse_file)
        lines = self.read_file(pulse_file_path, remove_comments=False)
        if 'GUI' not in lines[0]:
            warning_popup(
                """At this moment the GUI can't read pulse files that were not made by the GUI.\n
                   For now, the only option is to recreate the file in the GUI so it can be read by it again later.""",
            )
            return

        pulse_lines = self.read_file(pulse_file_path)
        sim_label_parts = pulse_file.split('PULSE.INP_', 1)
        sim_label = sim_label_parts[1] if len(sim_label_parts) > 1 else ''
        if self.PUMP_PROBE_LABEL in lines[0]:
            # Extract sim_label from filename for pump-probe files
            self.pump_probe_frame.load(pulse_lines, sim_label)
        else:
            self.sim_type_combo.current(1)

            tdse_file_path = Path(pulse_file.replace('PULSE', 'TDSE'))
            tdse_lines = self.read_file(tdse_file_path)

            self.custom_pulse_frame.load(pulse_lines, tdse_lines, sim_label)

        self.show_sim_type_frame()

    def get_outputs(self) -> None: ...

    def save(self) -> None:
        if self.sim_type_combo.get() == 'Pump-probe':
            ret = self.pump_probe_frame.save()
        else:
            ret = self.custom_pulse_frame.save()

        if not ret:
            return

        pulse_data, tdse_data, pulse_file_path, tdse_file_path, pulse_tabulation = ret

        if self.sim_type_combo.get() == 'Pump-probe':
            self.save_file(self.PUMP_PROBE_FILE, pulse_data, new_file_name=pulse_file_path)
        else:
            self.save_file(self.CUSTOM_PULSE_FILE, pulse_data, new_file_name=pulse_file_path)

        self.save_file(self.BASE_TDSE_FILE, tdse_data, new_file_name=tdse_file_path)

        for pulse_name, pulse_tabulation_data in pulse_tabulation.items():
            self.save_file_from_blank(Path(f'{pulse_name}.DAT'), pulse_tabulation_data)

    def print_irrep(self, _new_sym: bool = False) -> None: ...

    def run(self) -> None: ...
