"""
The pysmo package helps seismologists write new code to processes data. It does not
include any ready-made applications, but instead provides meaningful data structures that
make make writing code easier and more concise. Pysmo adds a layer between how data are
stored and how they are processed. This makes it easy to switch between data sources, use
multiple different ones simultaneously, as well as integrate with existing workflows. The
pysmo package consists of:

- :ref:`Pysmo types<types:Types>`: these are *protocol classes*, which define the
  types used in pysmo. They are intentially kept as simple as possible, and are
  derived from the types of data seismologists work with, rather than mirroring how
  data are stored in files.
- :ref:`Compatible classes<classes:Classes>`: while pysmo doesn't have a particlular
  *native* (file)format, it does rely on the classes holding seismological data to
  be compatible with the types defined by pysmo. Pysmo includes a minimal implementation
  of such a class for each type. They include additional methods or read-only attributes
  for the pysmo types. These minimal classes can be used as base classes when adopting
  existing classes to work with pysmo types, so that they may provide the same methods.
- :ref:`Functions<functions:Functions>`: pysmo includes functions that perform
  common operations on these data types. They are meant to be building blocks
  that can be used to construct more complex processing algorithms.
- :ref:`Tools<tools:tools>`: we place functions here that are too complex to be
  considered basic operations, make extensive use of other functions, or can be grouped
  together under a particular topic.
"""

from importlib.metadata import version
from pysmo.types import (
    Hypocenter,
    Location,
    Seismogram,
    Station,
)
from pysmo.classes.mini import (
    MiniSeismogram,
    MiniLocation,
    MiniStation,
    MiniHypocenter,
)
from pysmo.classes.sac import SAC

__version__ = version('pysmo')

__all__ = [
    'Location',
    'Hypocenter',
    'Seismogram',
    'Station',
    'SAC',
    'MiniSeismogram',
    'MiniLocation',
    'MiniStation',
    'MiniHypocenter',
]
