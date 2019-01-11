"""
The psymo.core.sac package consists of two modules, which provide:

    1. The python class :class:`SacIO`, to read and write SAC files.
    2. Functions which operate on the :class:`SacIO` class.
"""
from . import sacio, sacfunc
from .sacio import SacIO
from .sacfunc import *
