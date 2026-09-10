# flake8: noqa: E402, F403
"""Building-block functions for pysmo types.

--8<-- [start:in-the-box]
The [`pysmo.functions`][] module provides low-level functions that perform
common operations on [`pysmo`][] types. They are intended as building blocks
for constructing more complex processing workflows.
--8<-- [end:in-the-box]

Many functions accept a `replace` argument. Without it they modify the
seismogram in place and return `None`; with `replace=True` they leave the
input untouched and return a new seismogram. For example:

```python
>>> from pysmo.functions import resample
>>> from pysmo.classes import MSeed
>>> seis = MSeed.from_file("example.mseed")
>>> new_delta = seis.delta * 2
>>>
>>> # return a new seismogram, leaving seis untouched:
>>> new_seis = resample(seis, new_delta, replace=True)
>>>
>>> # modify data in seis directly:
>>> resample(seis, new_delta)
>>>
```

The new object is built from the input with [`copy.replace`][],
substituting only the freshly computed [`data`][pysmo.Seismogram.data]
(and, where the operation moves or resamples the time axis, the
corresponding [`begin_time`][pysmo.Seismogram.begin_time] or
[`delta`][pysmo.Seismogram.delta]). Every other attribute is carried
straight over from the input.

Warning: Attributes outside the `Seismogram` protocol
    A concrete class often carries more than `begin_time`, `delta` and
    `data`: identity, provenance or acquisition metadata. `replace=True`
    keeps those values as they were, even where the operation has made them
    a poor description of the new data, carrying each straight over by
    reference. If such an attribute is itself mutable, the input and the
    returned seismogram share the same object, so mutating it through one
    is visible through the other.

Not every concrete type supports `replace=True`: rebuilding the object this
way needs the substituted attributes to be constructor parameters.
[`MiniSeismogram`][pysmo.MiniSeismogram], [`MSeed`][pysmo.classes.MSeed] and
other value objects qualify; [`SacSeismogram`][pysmo.classes.SacSeismogram]
does not, because its `data` is a live view into an open SAC file rather
than a stored field.

```python
>>> from pysmo.functions import clone_to_mini, detrend
>>> from pysmo import MiniSeismogram
>>> from pysmo.classes import SAC
>>> sac = SAC.from_file("example.sac")
>>>
>>> # replace=True cannot rebuild a SacSeismogram:
>>> detrend(sac.seismogram, replace=True)
Traceback (most recent call last):
...
TypeError: ...
>>>
>>> # convert to a value object first (or copy the whole SAC object):
>>> detrended = detrend(clone_to_mini(MiniSeismogram, sac.seismogram), replace=True)
>>> type(detrended).__name__
'MiniSeismogram'
>>>
```

Note: Needless copy
    Reassigning the result back to the same name (`seis = resample(seis,
    new_delta, replace=True)`) ends up equivalent to modifying `seis` in
    place, but pays for a copy to get there. Call `resample(seis, new_delta)`
    directly instead.

Three helpers work with a seismogram as JSON:
[`seismogram_to_json`][pysmo.functions.seismogram_to_json] encodes a
value-object seismogram as a portable JSON document and
[`seismogram_from_json`][pysmo.functions.seismogram_from_json] reconstructs
it, while [`seismogram_checksum`][pysmo.functions.seismogram_checksum]
fingerprints one for change detection.

Hint: More functions live in `pysmo.tools`
    Additional functions may be found in [`pysmo.tools`][].
"""

from .._utils import export_module_names

_internal_names = set(dir())

from ._seismogram import *
from ._serialize import *
from ._utils import *

__all__ = [s for s in dir() if not s.startswith("_") and s not in _internal_names]

export_module_names(globals(), __name__)

del _internal_names
