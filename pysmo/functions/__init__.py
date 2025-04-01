"""
Simple operations using pysmo types.

This module provides functions that perform common operations using pysmo
types (mostly [`Seismogram`][pysmo.Seismogram]). They are meant to be building
blocks that can be used to construct more complex processing algorithms.

Many functions have a `clone` argument that controls whether the function
should operate on the input directly, or first create a clone of it (using
[`deepcopy`][copy.deepcopy]) and return the clone after using it for the
the function. For example:

```py
>>> from pysmo.function import resample
>>> from pysmo.classes import SAC
>>> sac_seis = SAC.from_file('testfile.sac').seismogram
>>> new_delta = sac_seis.delta * 2
>>>
>>> # create a clone and modify data in clone instead of sac_seis:
>>> new_sac_seis = resample(sac_seis, new_delta, clone=True)
>>>
>>> # modify data in sac_seis directly:
>>> resample(sac_seis, new_delta)
>>>
>>> # because the deepcopy operation can be computationaly expensive,
>>> # you should NOT use the following pattern:
>>> sac_seis = resample(sac_seis, new_delta, clone=True)
```

Hint:
    Additional functions may be found in [`pysmo.tools`][pysmo.tools].
"""

from ._seismogram import *  # noqa: F403
from ._utils import *  # noqa: F403

__all__ = []
__all__ += [s for s in dir() if not s.startswith("_")]
