---
icon: lucide/package-open
tags:
  - First steps
---

# Installing pysmo

## Prerequisites

Pysmo requires a recent Python version and depends on a small number of
third-party packages (e.g. [`NumPy`][numpy], [`SciPy`][scipy]). It is tested
against the latest three stable Python releases on Linux, MacOS, and Windows.

Pysmo is available from the
[Python Package Index](https://pypi.org/project/pysmo/) and can be installed
with [`pip`](https://pip.pypa.io/en/stable/):

=== "Stable"

    ```bash
    $ python3 -m pip install pysmo
    ```

=== "Pre-release"

    ```bash
    $ python3 -m pip install pysmo --pre
    ```
=== "Development Version"

    ```bash
    $ python3 -m pip install git+https://github.com/pysmo/pysmo
    ```

!!! tip
    The stable release can be installed alongside the development version.
    See the [development documentation](../development/index.md) for
    instructions.

## Upgrading

Upgrades to pysmo are also performed with the `pip` command:

```bash
python3 -m pip install -U pysmo
```

## Uninstalling

To remove pysmo from the system run:

```bash
python3 -m pip uninstall pysmo
```

!!! note
    `pip` does not remove dependencies that were automatically installed.
    Run `pip list` to see what is installed, then remove any unwanted packages
    with `pip uninstall`.
