"""
Functions used in signal processing.
"""

from ..._utils import export_module_names
from ._delay import delay
from ._gauss import envelope, gauss

__all__ = ["delay", "envelope", "gauss"]

export_module_names(globals(), __name__)
