# flake8: noqa: E402, F403
"""Signal processing functions for pysmo types.

Functions operate on pysmo [`Seismogram`][pysmo.Seismogram] objects and span
filtering, spectral analysis, delay estimation and array-wide arrival-time
refinement, instrument response removal, and frequency-domain calculus
(integration and differentiation). Filters are additionally registered in a
common registry, so they can be applied generically by name as well as by
calling the specific filter function directly.

Where a suitable implementation already exists in SciPy (e.g.
[`scipy.signal`][]), functions in this module wrap it rather than
reimplementing it; others implement seismology-specific algorithms with no
direct SciPy equivalent.

Functions that modify seismogram data follow the same `clone` convention as
[`pysmo.functions`][]: without `clone` they operate in place
and return `None`; with `clone=True` they return a modified copy.

!!! note

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
