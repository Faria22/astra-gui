"""TypedDict definitions for shared state in the time-dependent notebook."""

from typing import NotRequired, TypedDict


class PulseFileData(TypedDict):
    """Metadata required to fill pulse input templates."""

    type: str
    execute: str
    pulses: NotRequired[str]
    pulses_train: NotRequired[str]
    pump_pulses: NotRequired[str]
    pump_train: NotRequired[str]
    pump_probe_pulses: NotRequired[str]


class TdseFileData(TypedDict):
    """Metadata required to fill TDSE input templates."""

    pulse_filename: str
    structure_dir: str
    initial_time: float
    final_time: float
    final_pulse_time: float
    time_step: float
    save_time_step: float
    label: str


class TimeDependentState(TypedDict, total=False):
    """Cache for the most recent pulse configuration."""

    pulse_data: PulseFileData
    tdse_data: TdseFileData
    pulse_tabulation: dict[str, str]
