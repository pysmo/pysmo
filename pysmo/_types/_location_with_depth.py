from ._location import Location
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from attrs_strict import type_validator

__all__ = ["LocationWithDepth", "MiniLocationWithDepth"]


@runtime_checkable
class LocationWithDepth(Location, Protocol):
    """Protocol class to define the `LocationWithDepth` type."""

    @property
    def depth(self) -> float:
        """Location depth in metres."""
        ...

    @depth.setter
    def depth(self, value: float) -> None: ...


@define(kw_only=True, slots=True)
class MiniLocationWithDepth:
    """Minimal class for use with the [`MiniLocationWithDepth`][pysmo.MiniLocationWithDepth] type.

    The `MiniLocationWithDepth` class provides a minimal implementation of class that
    is compatible with the [`MiniLocationWithDepth`][pysmo.MiniLocationWithDepth] type.

    Examples:
        >>> from pysmo import MiniLocationWithDepth, LocationWithDepth, Location
        >>> my_hypo = MiniLocationWithDepth(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(my_hypo, LocationWithDepth)
        True
        >>> isinstance(my_hypo, Location)
        True
    """

    latitude: float | int = field(
        validator=[validators.ge(-90), validators.le(90), type_validator()],
    )
    """Location latitude from -90 to 90 degrees."""

    longitude: float | int = field(
        validator=[validators.gt(-180), validators.le(180), type_validator()],
    )
    """Location longitude from -180 to 180 degrees."""

    depth: float | int = field(validator=type_validator())
    """Location depth in metres."""
