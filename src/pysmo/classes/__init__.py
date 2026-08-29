# flake8: noqa: E402
"""Concrete classes compatible with pysmo types.

--8<-- [start:in-the-box]
The [`pysmo.classes`][] module provides classes that implement one or more
[`pysmo`][] protocol types. These classes can be used directly with any
pysmo function or tool that operates on pysmo types.
--8<-- [end:in-the-box]

Each class is designed with the protocol(s) it implements in mind, not to
reproduce its native format's full specification. The scope isn't strictly
limited to protocol attributes — [`pysmo.classes.StationXML`][], for
example, also carries epoch bookkeeping (`start_date`/`end_date`) and a
nested instrument `response` — but the protocol is the organising goal, not
fidelity to the format. Reconstructing a complete file for every supported
format is explicitly not a goal: where a class supports writing, the
guarantee is only that the output round-trips through that same class's own
reader, not that it satisfies the format's full external specification.
"""

from .._utils import export_module_names

_internal_names = set(dir())

from ._geocsv import *  # noqa: F403
from ._mseed import *  # noqa: F403
from ._quakeml import *  # noqa: F403
from ._sac import *  # noqa: F403
from ._sacpz import *  # noqa: F403
from ._stationxml import *  # noqa: F403

__all__ = [s for s in dir() if not s.startswith("_") and s not in _internal_names]

export_module_names(globals(), __name__)

del _internal_names
