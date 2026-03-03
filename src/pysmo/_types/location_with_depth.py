from .location import Location
from typing import Protocol, runtime_checkable
from attrs import define, field, validators, setters

__all__ = ["LocationWithDepth", "MiniLocationWithDepth"]


@runtime_checkable
class LocationWithDepth(Location, Protocol):
    """Protocol class to define the `LocationWithDepth` type."""

    depth: float
    """Location depth in metres."""


@define(kw_only=True, slots=True)
class MiniLocationWithDepth:
    """Minimal class for use with the [`LocationWithDepth`][pysmo.LocationWithDepth] type.

    The `MiniLocationWithDepth` class provides a minimal implementation of class that
    is compatible with the [`LocationWithDepth`][pysmo.LocationWithDepth] type.

    Examples:
        ```python
        >>> from pysmo import MiniLocationWithDepth, LocationWithDepth, Location
        >>> hypo = MiniLocationWithDepth(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(hypo, LocationWithDepth)
        True
        >>> isinstance(hypo, Location)
        True
        >>>
        ```
    """

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=float,
        validator=[validators.gt(-180), validators.le(180)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Location longitude from -180 to 180 degrees."""

    depth: float = field(
        converter=float, on_setattr=setters.pipe(setters.convert, setters.validate)
    )
    """Location depth in metres."""
