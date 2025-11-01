# Development Guidelines

This document captures the everyday conventions for contributors working on `astra_gui`. Use it as a checklist before opening a pull request.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for layout and naming. In practice this means four-space indentation, descriptive snake_case for variables and functions, PascalCase for classes, and readable lines (try to stay under 88 characters).
- `ruff check src tests` enforces our style. Run it locally and use `--fix` to auto-sort imports. Imports must be fully qualified (e.g., `from astra_gui.utils...`).
- Static typing matters: keep type hints up to date and verify them with `hatch run typecheck`.

## Docstrings and Inline Documentation

- Use concise, information-rich docstrings to describe modules, public classes, and functions. Module docstrings should summarize the feature area in a single paragraph.
- Format docstrings with the NumPy convention: summary line, blank line, followed by sections such as `Parameters`, `Returns`, `Raises`, and `Examples` when useful. Example:

```python
def solve(value: int) -> int:
    """Return the next valid solution.

    Parameters
    ----------
    value : int
        Seed value used to compute the next solution.

    Returns
    -------
    int
        The next solution in the sequence.
    """
    ...
```

- Prefer inline comments only when the intent of a block is not obvious from the code itself.

## Branching Workflow

- Create short-lived topic branches from `main`. Use descriptive prefixes: `feature/<issue-or-summary>`, `bugfix/<issue-or-summary>`, `docs/<topic>`, or `chore/<task>`.
- Keep branches focused on a single task and rebase interactively as needed to keep history clean.
- Delete feature branches after they are merged to avoid stale references.

## Commits and Pull Requests

- Write commits in the form `Verb scope`, for example `Add typechecking helpers` or `Fix parser edge cases`.
- Split formatting-only changes from behavioral work when practical.
- Pull requests should explain the change, note validation results (e.g., `hatch run all`), and reference related issues or tickets.

## Testing and Validation

- Pytest is our test runner. Add new test modules under `tests/` and name them `test_<feature>.py` with functions `test_<behavior>()`.
- Run `pytest tests` locally for quick verification. Before pushing, execute `hatch run all` to run Ruff, Basedpyright, and Pytest in one pass.
- When you add meaningful new behavior, create at least one smoke or integration test that exercises the end-to-end workflow so future changes cannot silently break it.

## Logging and Diagnostics

- GUI logging is configured via `astra_gui/utils/logger_module.py`. Pass `--debug` to `python -m astra_gui.cli` when you need verbose output during development.

Keeping these practices consistent helps contributors ramp quickly and ensures the GUI codebase stays healthy and predictable. Reach out to the maintainers if any guideline needs clarification or an update.
