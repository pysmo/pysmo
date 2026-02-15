---
icon: lucide/package-open
tags:
  - First steps
---

# Installing pysmo

## Prerequisites

Pysmo is built on top of standard [Python](https://www.python.org) and uses
some popular third party modules (e.g. [`NumPy`][numpy], [`SciPy`][scipy]).
In order to benefit from modern Python features and up to date modules, pysmo is
developed on the latest stable Python versions. Automatic tests are typically
run on the latest three stable Python releases on Linux, MacOS, and Windows.

Pysmo is available as a package from the
[Python Package Index](https://pypi.org/project/pysmo/). This means it can be easily
installed using the [`pip`](https://pip.pypa.io/en/stable/) module:

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
    It is possible to install the stable release alongside the development
    version. Please read the pysmo
    [development documentation](../developing/developing.md) for instructions.

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
    Unfortunately `pip` currently does not remove dependencies that were automatically
    installed. We suggest running `pip list` to see the installed packages, which
    can then also be removed using `pip uninstall`.
