"""Smoke tests to ensure top-level modules import correctly."""

import sys
from importlib import import_module
from pathlib import Path


def test_import_package_root() -> None:
    """Ensure the package is importable even if not installed in the environment."""
    src_path = Path(__file__).resolve().parents[1] / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    package = import_module('astra_gui')

    # Basic smoke check: importing populates the module namespace
    assert package.__dict__
