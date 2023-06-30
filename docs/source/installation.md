# Installing pysmo

## Prerequisites

Pysmo is built on top of standard [Python](https://www.python.org) and uses some popular
third party modules (e.g. [NumPy](inv:numpy#index), [SciPy](inv:scipy#index)). In order
to benefit from modern Python features and up to date modules, pysmo is developed on the
latest stable Python versions. Automatic tests are done on version 3.10 and newer.

Pysmo is available as a package from the
[Python Package Index](https://pypi.org/project/pysmo/). This means it can be easily
installed using the [`pip`](inv:pip#index) module:

```bash
$ python3 -m pip install pysmo
```

Pre-release versions of pysmo can be installed with the `--pre` flag:

```bash
$ python3 -m pip install pysmo --pre
```

Finally, the latest development version of pysmo can be installed directly from
[GitHub](https://github.com/pysmo/pysmo) by running:

```bash
$ python -m pip install git+https://github.com/pysmo/pysmo
```

```{note}
It is possible to install the stable release alongside the development
version. Please read the pysmo
[development documentation](<project:developing.md#development-environment>) for
instructions.
```

## Upgrading

Upgrades to pysmo are also performed with the ``pip`` command:

```bash
$ python3 -m pip install -U pysmo
```

## Uninstalling

To remove pysmo from the system run:

```bash
$ python3 -m pip uninstall pysmo
```

```{note}
Unfortunately `pip` currently does not remove dependencies that were automatically
installed. We suggest running `pip list` to see the installed packages, which can
then also be removed using `pip uninstall`.
```
