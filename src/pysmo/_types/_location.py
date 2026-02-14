from typing import Protocol, runtime_checkable
from attrs import define, field, validators

__all__ = ["Location", "MiniLocation"]


# --8<-- [start:location-protocol]


@runtime_checkable
class Location(Protocol):
    """Protocol class to define the `Location` type."""

    latitude: float
    """Latitude in degrees."""

    longitude: float
    """Longitude in degrees."""


# --8<-- [end:location-protocol]

# --8<-- [start:mini-location]


@define(kw_only=True, slots=True)
class MiniLocation:
    """Minimal class for use with the [`Location`][pysmo.Location] type.

    The `MiniLocation` class provides a minimal implementation of class that
    is compatible with the [`Location`][pysmo.Location] type.

    Examples:
        ```python
        >>> from pysmo import MiniLocation, Location
        >>> location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>> isinstance(location, Location)
        True
        >>>
        ```
    """

    latitude: float = field(validator=[validators.ge(-90), validators.le(90)])
    """Latitude from -90 to 90 degrees."""

    longitude: float = field(validator=[validators.gt(-180), validators.le(180)])
    """Longitude from -180 to 180 degrees."""


# --8<-- [end:mini-location]
