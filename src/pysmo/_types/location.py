from typing import Protocol

from attrs import define, field, setters, validators

from pysmo.lib.validators import convert_to_longitude

__all__ = ["Location", "MiniLocation"]


# --8<-- [start:location-protocol]


class Location(Protocol):
    """Protocol class to define the `Location` type."""

    latitude: float
    """Latitude in degrees."""

    longitude: float
    """Longitude in degrees."""


# --8<-- [end:location-protocol]

# --8<-- [start:mini-location]


@define(kw_only=True)
class MiniLocation:
    """Minimal class for use with the [`Location`][pysmo.Location] type.

    Examples:
        ```python
        >>> from pysmo import MiniLocation
        >>> location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>>
        ```
    """

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=convert_to_longitude,
        validator=[validators.gt(-180), validators.le(180)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Longitude from -180 to 180 degrees (-180 is stored as +180)."""


# --8<-- [end:mini-location]
