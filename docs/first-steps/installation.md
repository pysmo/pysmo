---
icon: lucide/package-open
tags:
  - First steps
---

# Installing pysmo

## Prerequisites

Pysmo depends on a small number of third-party packages (e.g. [`NumPy`][numpy],
[`SciPy`][scipy]) and makes use of modern Python language features. Python is
free and open-source software, so there is no good reason not to run the latest
stable release — and every reason to do so. Pysmo is tested against the latest
three stable Python releases on Linux, MacOS, and Windows.

## Virtual environments

It is good practice to install pysmo into a
[virtual environment](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
rather than the system Python. Virtual environments are self-contained and do
not require administrator privileges, making them well-suited to installing the
latest Python and keeping project dependencies isolated.

## Installing

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
