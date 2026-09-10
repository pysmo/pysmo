from typing import Protocol

from attrs import define, field, setters

from pysmo.lib.converters import to_longitude
from pysmo.lib.validators import is_latitude, is_longitude

from .location import Location

__all__ = ["LocationWithDepth", "MiniLocationWithDepth"]


class LocationWithDepth(Location, Protocol):
    """Protocol class to define the `LocationWithDepth` type.

    A [`Location`][pysmo.Location] that also carries a depth, such as an
    earthquake hypocentre.
    """

    depth: float
    """Location depth in metres, positive downwards."""


@define(kw_only=True)
class MiniLocationWithDepth:
    """Minimal implementation of the `LocationWithDepth` type.

    See [`LocationWithDepth`][pysmo.LocationWithDepth].

    Examples:
        ```python
        >>> from pysmo import MiniLocationWithDepth
        >>> hypo = MiniLocationWithDepth(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>>
        ```
    """

    latitude: float = field(
        converter=float,
        validator=is_latitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=to_longitude,
        validator=is_longitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location longitude from -180 to 180 degrees (-180 is stored as +180)."""

    depth: float = field(
        converter=float, on_setattr=setters.pipe(setters.convert, setters.validate)
    )
    """Location depth in metres, positive downwards."""
