---
icon: lucide/monitor-cog
tags:
  - Development
---

# Setting up

## Get the code

pysmo is developed on [GitHub](https://github.com/pysmo/pysmo). To contribute
changes back,
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) the
repository first, then clone the fork and add the main repository as a second
remote:

```bash
git clone git@github.com:<username>/pysmo.git
cd pysmo
git remote add upstream https://github.com/pysmo/pysmo.git
```

The `upstream` remote is used to pull in changes made after the fork. Cloning
over SSH avoids re-entering credentials on every push. A read-only checkout
without a fork works too:

```bash
git clone https://github.com/pysmo/pysmo.git
```

## Install with uv

pysmo uses [uv](https://docs.astral.sh/uv/) for development. uv manages the
virtual environment, the Python interpreter, and every dependency from a locked
set, so a checkout resolves to the same versions on any machine. Install uv,
then run:

```bash
make sync
```

This calls `uv sync`, which creates `.venv/` and installs pysmo with its
development, test, and documentation dependencies. uv downloads a suitable
Python version too if none is present.

Prefix commands with `uv run` to run them inside the environment, for example
`uv run pytest` or `uv run python`.

!!! tip "Drop the `uv run` prefix"

    [direnv](https://direnv.net) can activate the environment on entering the
    directory. Create `.envrc`:

    ```bash
    watch_file pyproject.toml uv.lock
    uv sync --quiet
    source .venv/bin/activate
    ```

    Then run `direnv allow`. `python`, `pytest`, and the rest now run directly.

## Make targets

Several development tasks are more than a single command. The `Makefile` bundles
them, and each target calls `uv` so nothing needs to be activated first.

| Command          | Action                                                                |
| ---------------- | --------------------------------------------------------------------- |
| `make sync`      | Install or update the environment from the lock file.                 |
| `make format`    | Apply `ruff` formatting, import sorting, and autofixes.               |
| `make lint`      | Check formatting and lint rules without changing files.               |
| `make mypy`      | Run the type checker.                                                 |
| `make tests`     | Run the full suite: `mypy`, `pytest`, coverage, and image comparison. |
| `make docs`      | Build the documentation into `site/`.                                 |
| `make live-docs` | Serve the documentation with live reload on `localhost:8000`.         |

`make help` lists them all.

## Testing every supported Python version

`make tests` runs the suite once, on the active interpreter.
[tox](https://tox.wiki) runs it in a fresh environment for each supported Python
version, the same matrix continuous integration uses:

```bash
uvx tox
```
