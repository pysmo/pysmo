"""
The pysmo package provides simple tools for seismologists to solve problems in a pythonic fashion.

Pysmo aims to simplify processing of seismic data by reducing what e.g. a seismogram actually is
to a minimal form, and provide single-purpose functions that operate on this form. With this in mind,
pysmo makes a clear distinction between data and processing; anything that can be derived from data
present in a seismogram should not be considered part of the seismogram itself. Similarily, we
believe the data should be completely unambiguous. A good example for this is how time is often
handled in seismic data; for certain tasks it may make sense to use different *kinds* of time (e.g.
relative to an event, first arrival, etc.), but in most cases this introduces unnecessary complexity
and potential for bugs (what if different kinds of times are accidentally mixed?). Pysmo only uses
absolute time, and instead relies on Python's powerful libraries for any calculations that may
become necessary.

The motivation for this rather strict approach is to provide well defined building blocks that
are easy to understand (and write!), and that can easily be combined to solve more complex
problems.
"""

from importlib.metadata import version
from pysmo.core.sac.sacio import SacIO  # noqa: F401
from pysmo.core.sac.sac import SAC  # noqa: F401
from pysmo.core.protocols import Seismogram, Event, Station  # noqa: F401
from pysmo.core.functions import *  # noqa: F401,F403

__version__ = version('pysmo')
