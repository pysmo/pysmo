from typing import Protocol

from attrs import define, field, setters

from pysmo.lib.converters import to_longitude
from pysmo.lib.validators import is_latitude, is_longitude

__all__ = ["Location", "MiniLocation"]


# --8<-- [start:location-protocol]


class Location(Protocol):
    """Protocol class to define the `Location` type.

    A geographic point, given as latitude and longitude in degrees.
    """

    latitude: float
    """Latitude in degrees."""

    longitude: float
    """Longitude in degrees."""


# --8<-- [end:location-protocol]

# --8<-- [start:mini-location]


@define(kw_only=True)
class MiniLocation:
    """Minimal implementation of the `Location` type.

    See [`Location`][pysmo.Location].

    Examples:
        ```python
        >>> from pysmo import MiniLocation
        >>> location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>>
        ```
    """

    latitude: float = field(
        converter=float,
        validator=is_latitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=to_longitude,
        validator=is_longitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Longitude from -180 to 180 degrees (-180 is stored as +180)."""


# --8<-- [end:mini-location]
