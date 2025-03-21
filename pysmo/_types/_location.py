from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from attrs_strict import type_validator

__all__ = ["Location", "MiniLocation"]


@runtime_checkable
class Location(Protocol):
    """The `Location` defines surface coordinates in pysmo.

    Attributes:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
    """

    @property
    def latitude(self) -> float: ...

    @latitude.setter
    def latitude(self, value: float) -> None: ...

    @property
    def longitude(self) -> float: ...

    @longitude.setter
    def longitude(self, value: float) -> None: ...


@define(kw_only=True)
class MiniLocation:
    """Minimal class for geographical locations.

    The `MiniLocation` class provides a minimal implementation of class that
    is compatible with the `Location` type.

    Attributes:
        latitude: The latitude of an object from -90 to 90 degrees.
        longitude: The longitude of an object from -180 to 180 degrees.

    Examples:
        >>> from pysmo import MiniLocation, Location
        >>> my_location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>> isinstance(my_location, Location)
        True
    """

    latitude: float | int = field(
        validator=[validators.ge(-90), validators.le(90), type_validator()],
    )
    longitude: float | int = field(
        validator=[validators.gt(-180), validators.le(180), type_validator()],
    )
