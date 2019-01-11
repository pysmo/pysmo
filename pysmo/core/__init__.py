"""
The pysmo package provides some simple to use tools for seismologists.

It's core components are an interface to the commonly used
`SAC file format <https://ds.iris.edu/files/sac-manual/manual/file_format.html>`_,
functions that work with this interface, and some additional useful tools.
"""

from . import sac
from .sac import *
