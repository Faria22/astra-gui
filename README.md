# ASTRA GUI

[![PyPI - Version](https://img.shields.io/pypi/v/astra-gui.svg)](https://pypi.org/project/astra-gui)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/astra-gui.svg)](https://pypi.org/project/astra-gui)

-----

ASTRA GUI provides a desktop interface for preparing and running ASTRA workflows. It ships ready-to-use notebook pages for common time-dependent and time-independent calculations, wraps the ASTRA command-line tools, and keeps input templates and run configurations organized.

## Requirements

- Python 3.10–3.13 (CPython)
- Tkinter (GUI toolkit used by the application)
- ASTRA binaries available on your `PATH`

### Install Tkinter

Tkinter is bundled with some Python distributions but not all. The GUI will not start without it.

**macOS**

- If you installed Python from [python.org](https://www.python.org/downloads/), Tkinter is already included—no extra action required.
- For Homebrew Python, install the matching Tk bindings:

  ```console
  brew install python-tk
  ```

  Homebrew publishes versioned formulae (for example `python-tk@3.12`); install the one that matches the Python you are using and follow any `brew link` instructions it prints.

**Linux**

- Debian/Ubuntu and derivatives:

  ```console
  sudo apt-get update
  sudo apt-get install python3-tk
  ```

- Fedora/RHEL and derivatives:

  ```console
  sudo dnf install python3-tkinter
  ```

- Arch Linux:

  ```console
  sudo pacman -S tk
  ```

Refer to your distribution’s package manager if it uses different names.

### Verify Tkinter Is Available

After installation, confirm Tkinter works by launching the self-test. A small window labeled “Tk” should appear.

```console
python3 -m tkinter
```

If you receive `ModuleNotFoundError: No module named '_tkinter'`, reinstall Tkinter for the interpreter you are using.

## Installation

Install the latest release from PyPI:

```console
pip install astra_gui
```

## Launching the GUI

Once installed, run ASTRA GUI from the terminal:

```console
astra_gui
```

Add the `--debug` flag to enable verbose logging if you are diagnosing issues.

## Configure ASTRA Paths

ASTRA GUI shells out to the ASTRA binaries, so it must be able to find them through environment variables such as `PATH`, `ASTRA_HOME`, or any custom variables your installation requires.

- When you connect to a machine with `ssh`, Bash starts as a *login shell*. Login shells read `~/.bash_profile` (or `~/.profile`) first and skip `~/.bashrc` unless it is explicitly sourced. If you only export your ASTRA paths in `~/.bashrc`, they will be missing when you launch ASTRA GUI over SSH.
- Add the relevant exports directly to `~/.bash_profile` so they load for login shells:

  ```bash
  # ~/.bash_profile
  export ASTRA_HOME="$HOME/astra"
  export PATH="$ASTRA_HOME/bin:$PATH"
  ```

This ensures the environment is configured both locally and for remote SSH sessions.

## Remote Connections and Notifications

ASTRA GUI supports SSH-backed runs and completion alerts. Configure remote access through **Settings ▸ SSH**; add the target host, user, and key to your `~/.ssh/config` so the dialog can reuse those settings. Enable run notifications via **Settings ▸ Notifications**, then select `Email` or `NTFY` and supply the destination address or topic to receive status updates.

Detailed walkthroughs live in the GUI under **Help** in the menu bar.

## Developer Setup

Clone the repository and install the project in development mode:

```console
git clone https://github.com/Faria22/astra_gui.git
cd astra_gui
pip install -e .[dev]
```

Use Hatch to run the standard quality checks:

```console
hatch run all   # Ruff, basedpyright, and pytest
```

## License

`astra_gui` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
