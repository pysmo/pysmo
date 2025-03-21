from ._location import Location, MiniLocation
from typing import Protocol, runtime_checkable
from attrs import define, field
from attrs_strict import type_validator

__all__ = ["Hypocenter", "MiniHypocenter"]


@runtime_checkable
class Hypocenter(Location, Protocol):
    """The `Hypocenter` class defines a protocol for hypocenters in pysmo.

    Attributes:
        depth: Event depth in metres.
        latitude (float): Latitude in degrees.
        longitude (float): Longitude in degrees.
    """

    @property
    def depth(self) -> float: ...

    @depth.setter
    def depth(self, value: float) -> None: ...


@define(kw_only=True)
class MiniHypocenter(MiniLocation):
    """Minimal class for hypocententers.

    The `MiniHypocenter` class provides a minimal implementation of class that
    is compatible with the [`Hypocenter`][pysmo.Hypocenter] type. The
    class is a subclass of [`MiniLocation`][pysmo.MiniLocation],
    and therefore also matches the [`Location`][pysmo.Location] type.

    Attributes:
        depth: Hypocenter depth.
        longitude (float): Event longitude.
        latitude (float): Event latitude.

    Examples:
        >>> from pysmo import MiniHypocenter, Hypocenter, Location
        >>> my_hypo = MiniHypocenter(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(my_hypo, Hypocenter)
        True
        >>> isinstance(my_hypo, Location)
        True
    """

    depth: float | int = field(validator=type_validator())
