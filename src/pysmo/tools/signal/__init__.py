# flake8: noqa: E402, F403
"""
Signal processing functions for pysmo types.

Most functions in this module are convenience wrappers around
[`scipy.signal`][] adapted to accept pysmo
[`Seismogram`][pysmo.Seismogram] objects. This covers filtering
([`bandpass`][pysmo.tools.signal.bandpass],
[`lowpass`][pysmo.tools.signal.lowpass], etc.) and spectral analysis
([`psd`][pysmo.tools.signal.psd], [`envelope`][pysmo.tools.signal.envelope]).

Functions that modify seismogram data follow the same `clone` convention as
[`pysmo.functions`][]: without `clone` they operate in place
and return `None`; with `clone=True` they return a modified copy.

Specialised functions not found in SciPy include cross-correlation based
delay estimation ([`delay`][pysmo.tools.signal.delay],
[`multi_delay`][pysmo.tools.signal.multi_delay]) and the MCCC
arrival-time solver ([`mccc`][pysmo.tools.signal.mccc]).

!!! warning

    The [`Seismogram`][pysmo.Seismogram] type carries no unit label for
    `data`. Functions in this module do not track or convert physical
    units either — e.g. [`remove_response`][pysmo.tools.signal.remove_response]
    outputs whatever quantity the given response's `input_units` declares,
    and [`integrate`][pysmo.tools.signal.integrate]/
    [`differentiate`][pysmo.tools.signal.differentiate] shift between
    displacement/velocity/acceleration without recording which is which.
    Callers must keep track of the physical quantity `seismogram.data`
    represents.
"""

from ..._utils import export_module_names

_internal_names = set(dir())

from ._calculus import *
from ._delay import *
from ._filter import *
from ._response import *
from ._spectral import *

__all__ = [s for s in dir() if not s.startswith("_") and s not in _internal_names]

export_module_names(globals(), __name__)

del _internal_names
