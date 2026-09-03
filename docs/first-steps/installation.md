---
icon: lucide/package-open
tags:
  - First steps
---

# Installing pysmo

## Requirements

Pysmo needs a few packages from PyPI ([`NumPy`][numpy], [`SciPy`][scipy], and
others), all installed automatically. It runs on Python
{{ python_versions_phrase }} on Linux, macOS, and Windows.

## A project (recommended)

Installing packages by hand is fiddly. It means creating a virtual environment,
activating it, and running `pip install` for each package. It is also easy to
lose track of what is installed.

Software-development tools automate this. That helps anyone running Python, not
only developers. [uv](https://docs.astral.sh/uv/) creates the environment,
installs Python when needed, and records each package added.

Create a project and add pysmo, plus mypy for the [next chapter](tutorial.md):

```bash
uv init my-analysis
cd my-analysis
uv add pysmo
uv add --dev mypy  # tooling, separate from the code's dependencies
```

`uv add` records pysmo in `pyproject.toml`. It also pins the full dependency
tree in `uv.lock`. From those two files the environment can be rebuilt exactly,
later or on another machine. Commit both.

Run code with uv:

```bash
uv run my_script.py
uv run mypy my_script.py
```

Elsewhere, `uv sync` restores the environment from those two files.

!!! tip "Drop the `uv run` prefix"

    [direnv](https://direnv.net) can activate the project environment on entering
    the directory, so `python`, `mypy`, and other tools run directly. Create
    `.envrc`:

    ```bash
    watch_file pyproject.toml uv.lock
    uv sync --quiet
    source .venv/bin/activate
    ```

    Then run `direnv allow`. The environment now tracks `pyproject.toml` and
    `uv.lock` automatically.

## A single script

For a one-off analysis, uv can attach dependencies to a single file instead of a
project directory. They go in a metadata block at the top of the script.

```bash
uv init --script analysis.py
uv add --script analysis.py pysmo
uv run analysis.py
```

`uv run` installs the listed dependencies before running the script.

Type-checking a single-file script is less convenient: a script's inline
dependencies are not visible to a separately-invoked type checker. For anything
involving mypy, the project layout above is smoother.

## Installing into an existing environment

To install pysmo into an environment managed another way (a virtual environment
or a conda environment), activate it and use
[`pip`](https://pip.pypa.io/en/stable/):

```bash
python3 -m pip install pysmo
```

Prefer a
[virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
over the system Python. It needs no administrator rights and keeps each
project's dependencies separate.

## Pre-release and development versions

The commands above install the latest stable release. For a pre-release or the
development version from GitHub:

=== "Project"

    ```bash
    uv add pysmo --prerelease allow
    uv add "pysmo @ git+https://github.com/pysmo/pysmo"
    ```

=== "Script"

    ```bash
    uv add --script analysis.py pysmo --prerelease allow
    uv add --script analysis.py "pysmo @ git+https://github.com/pysmo/pysmo"
    ```

=== "pip"

    ```bash
    python3 -m pip install pysmo --pre
    python3 -m pip install "git+https://github.com/pysmo/pysmo"
    ```

## Upgrading

=== "Project"

    ```bash
    uv sync --upgrade-package pysmo
    ```

=== "Script"

    ```bash
    uv sync --script analysis.py --upgrade-package pysmo
    ```

=== "pip"

    ```bash
    python3 -m pip install -U pysmo
    ```

## Removing

=== "Project"

    ```bash
    uv remove pysmo
    ```

=== "Script"

    ```bash
    uv remove --script analysis.py pysmo
    ```

=== "pip"

    ```bash
    python3 -m pip uninstall pysmo
    ```

    `pip` leaves automatically-installed dependencies behind. `pip list` shows what
    is installed. Remove anything unwanted with `pip uninstall`.
