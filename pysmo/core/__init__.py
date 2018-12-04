"""
The pysmo package provides some simple to use tools for seismologists.

It's core components are an interface to the commonly used
`SAC file format <https://ds.iris.edu/files/sac-manual/manual/file_format.html>`_,
functions that work with this interface, and some additional useful tools.
"""

from __future__ import division, absolute_import, print_function
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
from . import sac
from .sac import SacIO, sacfunc
