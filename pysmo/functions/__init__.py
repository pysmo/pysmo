"""
Simple operations using pysmo types.

This module provides functions that perform common operations using pysmo
types (mostly [`Seismogram`][pysmo.Seismogram]). They are meant to be building
blocks that can be used to construct more complex processing algorithms.

In many cases these functions return the same type of
[`Seismogram`][pysmo.Seismogram] objects that they receive as input. This
involves [deep copying][copy.deepcopy] the input objects, which can come at some
computational cost. To mitigiate this, many functions are also available as
methods in the [`MiniSeismogram`][pysmo.MiniSeismogram] class.

Hint:
    Additional functions may be found in [`pysmo.tools`][pysmo.tools].
"""

from ._seismogram import *  # noqa: F403

__all__ = []
__all__ += [s for s in dir() if not s.startswith("_")]
