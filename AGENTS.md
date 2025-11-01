# Repository Guidelines

## Project Structure & Module Organization
- Source lives under `src/astra_gui/`, grouped by feature (GUI notebooks, utils, time-dependent/independent flows).
- Tests reside in `tests/`; smoke tests sit at the package root.
- Shared assets (input templates, help text) are inside `src/astra_gui/input_file_templates/` and `src/astra_gui/help_messages/`.

## Build, Test, and Development Commands
- `hatch run all`: Runs Ruff, basedpyright, and pytest; use before any push.
- `hatch run typecheck`: Executes basedpyright for static typing verification.
- `ruff check src tests`: Lints Python modules; append `--fix` to auto-sort imports.

## Coding Style & Naming Conventions
- Follow Ruff (PEP 8-aligned) formatting; imports must be fully-qualified (e.g., `from astra_gui.utils...`).
- Indentation is 4 spaces; prefer descriptive snake_case for variables/functions and PascalCase for classes.
- Keep docstrings concise and prefer module-level summaries where relevant.

## Testing Guidelines
- Pytest is the primary framework; place new suites under `tests/`.
- Name tests `test_<feature>.py` with functions `test_<behavior>()`.
- Ensure new features include at least a smoke or integration test; run `pytest tests` locally before committing.

## Commit & Pull Request Guidelines
- Commit messages follow an imperative verb plus scope (e.g., `Add typechecking helpers`).
- Keep commits focused; split formatting-only changes when practical.
- Pull requests should describe the change, list validation (`hatch run all`), and reference related issues or tickets.

## Configuration & Environment Notes (Optional)
- GUI logging is configured via `astra_gui/utils/logger_module.py`; pass `--debug` when invoking `python -m astra_gui.cli` to enable verbose logs.
