"""
Pysmo protocol classes and their minimal implementations.

--8<-- [start:in-the-box]
The [`pysmo`][] base namespace provides protocol classes used as type hints
and a minimal reference implementation ("Mini class") for each protocol.
The protocols define common seismological data structures such as locations,
seismic events, stations, and seismograms.

Each Mini class is a concrete [`attrs`][] class that implements exactly the
attributes required by its protocol. Mini classes are named by prefixing
"Mini" to the protocol name (e.g. [`MiniSeismogram`][pysmo.MiniSeismogram]
implements the [`Seismogram`][pysmo.Seismogram] protocol).
--8<-- [end:in-the-box]

Classes, functions, and other tools that operate on pysmo types are provided
by the [`pysmo.classes`][], [`pysmo.functions`][], and [`pysmo.tools`][]
subpackages.
"""

from importlib.metadata import version
from ._utils import export_module_names


from ._types import (
    Seismogram,
    Station,
    Event,
    Location,
    LocationWithDepth,
    MiniSeismogram,
    MiniStation,
    MiniEvent,
    MiniLocation,
    MiniLocationWithDepth,
)

__version__ = version("pysmo")


__all__ = [
    "Seismogram",
    "Station",
    "Event",
    "Location",
    "LocationWithDepth",
    "MiniSeismogram",
    "MiniStation",
    "MiniEvent",
    "MiniLocation",
    "MiniLocationWithDepth",
]

type _BaseProto = Seismogram | Station | Event | Location | LocationWithDepth
type _BaseMini = (
    MiniSeismogram | MiniStation | MiniEvent | MiniLocation | MiniLocationWithDepth
)

export_module_names(globals(), __name__)
