"""
Functions used in signal processing.
"""

from ._delay import delay
from ._gauss import envelope, gauss


__all__ = ["delay", "envelope", "gauss"]
