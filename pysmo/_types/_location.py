from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from attrs_strict import type_validator

__all__ = ["Location", "MiniLocation"]


@runtime_checkable
class Location(Protocol):
    """Protocol class to define the `Location` type."""

    @property
    def latitude(self) -> float:
        """Latitude in degrees."""
        ...

    @latitude.setter
    def latitude(self, value: float) -> None: ...

    @property
    def longitude(self) -> float:
        """Longitude in degrees."""
        ...

    @longitude.setter
    def longitude(self, value: float) -> None: ...


@define(kw_only=True, slots=True)
class MiniLocation:
    """Minimal class for use with the [`Location`][pysmo.Location] type.

    The `MiniLocation` class provides a minimal implementation of class that
    is compatible with the [`Location`][pysmo.Location] type.

    Examples:
        >>> from pysmo import MiniLocation, Location
        >>> my_location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>> isinstance(my_location, Location)
        True
    """

    latitude: float | int = field(
        validator=[validators.ge(-90), validators.le(90), type_validator()],
    )
    """Latitude from -90 to 90 degrees."""

    longitude: float | int = field(
        validator=[validators.gt(-180), validators.le(180), type_validator()],
    )
    """Longitude from -180 to 180 degrees."""
