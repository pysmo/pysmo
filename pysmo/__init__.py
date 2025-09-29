"""
Pysmo types and corresponding Mini Classes.

The psymo base namespace exposes the protocol classes that are used as type
hints, as well as reference implementations of a generic class for each
protocol. The reference classes are subclasses of their respective protocol
classes that contain exactly the same attributes (though some extra methods may
be defined for convenience). They can be considered minimal implementations of
a class that can be used with pysmo protocols, and are therefore named "Mini" +
"name of protocol" (e.g. [`MiniSeismogram`][pysmo.MiniSeismogram] is an
implementation of the [`Seismogram`][pysmo.Seismogram] type).

Classes, functions and other tools that make use of pysmo types and mini
need to be imported from other modules.
"""

from importlib.metadata import version


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
