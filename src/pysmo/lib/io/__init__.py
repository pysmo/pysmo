"""Low-level I/O classes for reading and writing seismological file formats.

Classes in this module handle file format details but do not implement
[`pysmo`][] protocol types directly. They serve as the foundation for
the higher-level classes in [`pysmo.classes`][] and should generally not
be used directly.
"""

from ._sacio import SacIO
from ..._utils import export_module_names

__all__ = [
    "SacIO",
]

export_module_names(globals(), __name__)
