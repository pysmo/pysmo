"""I/O classes.

This module contains classes that are not compatible with
pysmo types, but serve as bases for classes that are. This
means all functionality in this modules is available elsewhere,
and these classes should *not* be used directly by users.
"""

from ._sacio.sacio import SacIO, SacHeaderUndefined

SacHeaderUndefined = SacHeaderUndefined

__all__ = [
    "SacIO",
]
