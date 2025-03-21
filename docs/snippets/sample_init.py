"""
The psymo package uses protocols to define types that focus on the essence of
seismological data (i.e. what they are in the pyhsical world, rather than the
abstract ways they may be stored in a file or inside an application). This
enables useres to write code that is more intuitive to understand and more
reusable across different projects or applications.

The psymo base namespace exposes the protocol classes that are used as type
hints, as well as reference implementations of a generic class for each
protocol. The reference classes are subclasses of their respective protocol
classes that contain exactly the same attributes (though some extra methods may
be defined for convenience). They can be considered minimal implementations of
a class that can be used with pysmo protocols, and are therefore named "Mini" +
"name of protocol" (e.g. [`MiniSeismogram`][pysmo.MiniSeismogram] is an
implementation of the [`Seismogram`][pysmo.Seismogram] type).
"""

from importlib.metadata import version


from ._types import (
    Seismogram,
    Location,
    Hypocenter,
    Station,
    Event,
    MiniSeismogram,
    MiniLocation,
    MiniStation,
    MiniHypocenter,
    MiniEvent,
)


__version__ = version("pysmo")


__all__ = [
    "Seismogram",
    "Location",
    "Hypocenter",
    "Station",
    "Event",
    "MiniSeismogram",
    "MiniLocation",
    "MiniStation",
    "MiniHypocenter",
    "MiniEvent",
]
