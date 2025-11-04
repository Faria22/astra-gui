"""TypedDict definitions for shared state in the time-independent notebook."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from numpy.typing import NDArray

CapStrengthRow = list[str | float]
CapStrengths = dict[str, list[CapStrengthRow]]


class TimeIndependentState(TypedDict, total=False):
    """Cache for the most recent CAP and CC metadata."""

    cap_radii: list[str]
    cap_strengths: CapStrengths
    cc_syms: list[str]
    computed_syms: list[str]
    target_states_data: NDArray[Any]
    open_channels: list[bool]
