# Pysmo root folder

This is the root folder of the `pysmo` module.

**Table of Contents**

- [classes](#classes)
- [functions](#functions)
- [\_\_init__.py](#__init__.py)
- [io](#io)
- [tools](#tools)
- [types.py](#types.py)

## classes

The [`classes`](classes) folder contains the data classes that are compatible with pysmo types

## functions

The [`functions`](functions) folder contains functions that use pysmo types as input and/or output. These are supposed to be relatively simple functions that can be used as building blocks to solve more complex task.

## \_\_init__.py

The [`__init__.py`](__init__.py) file serves the following purposes:

1. It contains content for the for the documentation (i.e. the docstring is used in the "What's in the Chapter").
2. Makes pysmo types available by importing them from [`types.py`](types.py)
3. Makes psymo classes available by importing them from the files contained in the [`classes`](classes) folder.

The other components (e.g. functions) use their own `__init__.py` files.

## io

The [io](io) folder contains Python classes that are _not_ compatible with pysmo types, but serve as base classes to build on top of to create compatible ones. Typically they are used to read/write to specific file formats.

## tools

The [tools](tools) folder contains useful additions that may or may not use pysmo types, or use combinations of multiple pysmo functions to create more "standalone" applications.

## types.py

The [types.py](types.py) file contains all of pysmo's types.