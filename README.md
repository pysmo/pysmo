
[![Test Status](https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml/badge.svg)](https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml)
[![Build Status](https://github.com/pysmo/pysmo/actions/workflows/build.yml/badge.svg)](https://github.com/pysmo/pysmo/actions/workflows/build.yml)
[![Documentation Status](https://readthedocs.org/projects/pysmo/badge/?version=latest)](https://pysmo.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/pysmo/pysmo/branch/master/graph/badge.svg?token=ZsHTBN4rxF)](https://codecov.io/gh/pysmo/pysmo)
[![PyPI](https://img.shields.io/pypi/v/pysmo)](https://pypi.org/project/pysmo/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pysmo)

Pysmo
=====

The pysmo package provides simple tools for seismologists to solve problems in a pythonic fashion.


Quickstart
----------
To install the stable version of pysmo run the following command in a terminal:

```shell
$ pip install pysmo
```

Pre-release versions of pysmo can be installed by running:

```shell
$ pip install pysmo --pre
```

Finally, to install the current ``master`` branch directly from Github run:

```shell
$ pip install git+https://github.com/pysmo/pysmo
```

Pysmo can then be used in a python script or the python shell directly:


```python
>>> from pysmo import SAC
>>> seismogram = SAC.from_file('file.sac')
>>> print(seismogram.delta)
0.02500000037252903
>>> print(seismogram.data)
[-2.987490077543953e-08, -2.983458813332618e-08, ...
>>> help(SAC)
Help on class SAC in module pysmo object:

...
```
Documentation
-------------

The complete pysmo documentation is available at https://pysmo.readthedocs.io/

Contributors
------------

- Helio Tejedor
