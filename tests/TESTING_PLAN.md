# ASTRA GUI Testing Roadmap

## Foundations
- Create `tests/conftest.py` providing a headless `tk.Tk` root (withdrawn), patched `messagebox`/`filedialog`, temporary config directory fixtures, Paramiko stubs, fake notebooks, template path factories, and a shared RNG seed helper.
- Add `pytest.ini` (or update existing configuration) defining markers (`unit`, `gui`, `integration`) and baseline coverage targets to track incremental progress.

## CLI & Application Shell
- Add unit tests for `astra_gui.cli` argument parsing covering flag combinations, mutual exclusion, defaults, and path requirements.
- Write integration-style tests for `astra_gui.app.Astra` that inject fake notebooks and `SshClient` instances to validate geometry handling, status bar messaging, running-directory selection (local and remote), menu bindings, and notebook routing.

## GUI Notebooks
- Exercise `home_screen.HomeNotebook`, `close_coupling.create_cc_notebook.CreateCcNotebook`, `time_independent.time_independent_notebook.TimeIndependentNotebook`, `time_dependent.time_dependent_notebook.TimeDependentNotebook`, and their respective page modules to confirm tabs register, widgets render, and lifecycle callbacks (`load`, `erase`, `save`, `run`, `print_irrep`, `get_outputs`) interact with controllers correctly.
- Use reusable fixture notebooks plus snapshot/assertion helpers to validate widget trees and Tk callback wiring without requiring a live GUI.

## Infrastructure & Utilities
- Extend coverage for `utils.config_module`, `logger_module`, `notification_module`, `statusbar_module`, `popup_module`, `font_module`, `hover_widget_module`, `scrollable_module`, `table_module`, `symmetry_module`, and `notebook_module` helper functions, including error branches and boundary cases.
- Parameterize tests where possible (e.g., symmetry combinations, table column layouts) and rely on monkeypatched Tk/interprocess primitives for deterministic behaviour.

## Remote & Persistence Layers
- Build focused tests for `utils.ssh_client` using fake `paramiko.SSHClient`/`SFTPClient` objects to cover configuration lookup, connection failure modes, SFTP exceptions, remote path normalisation, and host persistence.
- Cover popup interactions that depend on `SshClient` outcomes to ensure message routing remains correct.

## Domain Flows & Assets
- Validate close-coupling creators (`close_coupling.dalton`, `lucia`, `molecule`, `bsplines`, `clscplng`) and time-independent modules (`pad`, `structural`, `scatt_states`) by supplying representative configuration data and asserting generated input files, symmetry selections, and warning flows.
- Add numerical tests for `time_dependent.pulse.Pulse`/`Pulses` to confirm parameter coercion, envelope calculations, tabulation output, and error handling on invalid shapes.
- Introduce smoke tests that load every template in `input_file_templates/` and `help_messages/`, verifying readability and newline conventions, and run CLI entry points (`python -m astra_gui.cli --help`, minimal notebook invocations) to guarantee packaging integrity.

## TDD Cadence & Process
- Adopt a per-module workflow: write a failing test, implement the minimal code change, refactor, and extend coverage for edge cases before progressing.
- Treat “definition of done” as updated/added tests plus a passing `hatch run all`, and track coverage deltas in PR descriptions with a target to raise coverage roughly 5% per milestone until stabilising near 80%.
- When encountering new GUI or remote concerns, add reusable fixtures/fakes immediately so subsequent work benefits from consistent tooling.
- For every defect fix, add a regression test in the relevant module and schedule periodic smoke-test enhancements (e.g., scripted round-trips through CC/TI/TD flows) to keep high-level behaviour locked down.
