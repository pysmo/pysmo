# Pysmo lib folder

**Table of Contents**

- [decorators.py](#decorators.py)
- [defaults.py](#defaults.py)
- [exceptions.py](#exceptions.py)
- [functions.py](#functions.py)
- [io](#io)

## decorators.py

The [`decorators.py`](decorators.py) file contains decoratos used in pysmo.

## defaults.py

The [`defaults.py`](defaults.py) file contains default values used throughout pysmo.

## exceptions.py

The [`exceptions.py`](exceptions.py) file contains custom exception classes for pysmo.

## functions.py

The [`functions.py`](functions.py) file contains functions that don't
use pysmo types directly, but are used within functions that do.
To make it clear that these functions are more for internal use,
they are prefixed with `lib_`.

## io

The [`io`](io) folder contains classes that interface with standard
data files used in seismology. They are used as base classes
for classes that are compatible with pysmo types.
