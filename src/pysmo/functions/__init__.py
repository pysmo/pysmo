# flake8: noqa: E402, F403
"""
Building-block functions for pysmo types.

--8<-- [start:in-the-box]
The [`pysmo.functions`][] module provides low-level functions that perform
common operations on [`pysmo`][] types. They are intended as building blocks
for constructing more complex processing workflows.
--8<-- [end:in-the-box]

Many functions accept a `clone` argument that controls whether the function
operates on the input directly or first creates a clone (via
[`deepcopy`][copy.deepcopy]) and returns the modified copy. For example:

```python
>>> from pysmo.functions import resample
>>> from pysmo.classes import SAC
>>> sac_seis = SAC.from_file("example.sac").seismogram
>>> new_delta = sac_seis.delta * 2
>>>
>>> # create a clone and modify data in clone instead of sac_seis:
>>> new_sac_seis = resample(sac_seis, new_delta, clone=True)
>>>
>>> # modify data in sac_seis directly:
>>> resample(sac_seis, new_delta)
>>>
```

Note:
    Avoid `sac_seis = resample(sac_seis, new_delta, clone=True)` when you intend
    to modify `sac_seis` in place. The [`deepcopy`][copy.deepcopy] operation is
    computationally expensive and unnecessary — use `resample(sac_seis, new_delta)`
    instead.

Hint:
    Additional functions may be found in [`pysmo.tools`][pysmo.tools].
"""

from .._utils import export_module_names

_internal_names = set(dir())

from ._seismogram import *
from ._utils import *

__all__ = [s for s in dir() if not s.startswith("_") and s not in _internal_names]

export_module_names(globals(), __name__)

del _internal_names
