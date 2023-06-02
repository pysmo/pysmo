"""
The pysmo package helps seismologists write new code to processes data. It does not
include any ready-made applications, but instead provides meaningful data structures that
make make writing code easier and more concise. Pysmo adds a layer between how data are
stored and how they are processed. This makes it easy to switch between data sources, use
multiple different ones simultaneously, as well as integrate with existing workflows. The
pysmo package consists of:

- [Pysmo types](<project:types.md#Types>): these are *protocol classes*, which define the
  types used in pysmo. They are intentially kept as simple as possible, and are
  derived from the types of data seismologists work with, rather than mirroring how
  data are stored in files.
- [Functions](<project:functions.md#Functions>): pysmo includes functions that perform
  common operations on these data types. They are meant to be building blocks
  that can be used to construct more complex processing algorithms.
- [Tools](<project:tools.md#Tools>): we place functions here that are too complex to be
  considered basic operations, make extensive use of other functions, or can be grouped
  together under a particular topic.
"""

from importlib.metadata import version
from pysmo.core.sac.sacio import _SacIO  # noqa: F401
from pysmo.core.sac.sac import SAC  # noqa: F401
from pysmo.core.protocols import *  # noqa: F401,F403
from pysmo.core.functions import *  # noqa: F401,F403

__version__ = version('pysmo')
