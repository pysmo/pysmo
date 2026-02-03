"""Typing related items."""

from typing import get_args, TypeAlias
from pysmo import (
    Event,
    Location,
    LocationWithDepth,
    Seismogram,
    Station,
    MiniEvent,
    MiniLocation,
    MiniLocationWithDepth,
    MiniSeismogram,
    MiniStation,
)
from pysmo.tools.iccs import ICCSSeismogram, MiniICCSSeismogram

_AnyProto: TypeAlias = (
    Event | Location | LocationWithDepth | Seismogram | Station | ICCSSeismogram
)
"Type alias for any pysmo Protocol class."

_AnyMini: TypeAlias = (
    MiniEvent
    | MiniLocation
    | MiniLocationWithDepth
    | MiniSeismogram
    | MiniStation
    | MiniICCSSeismogram
)
"Type alias for any pysmo Mini class."


def proto2mini(proto: type[_AnyProto]) -> tuple[_AnyMini, ...]:
    """Returns valid Mini classes for a given pysmo type."""
    return tuple(
        mini for mini in get_args(_AnyMini) if proto in matching_pysmo_types(mini)
    )


def matching_pysmo_types(obj: object) -> tuple[_AnyProto, ...]:
    """Returns pysmo types that objects may be an instance of.

    Parameters:
        obj: Name of the object to check.

    Returns:
        Pysmo types for which `obj` is an instance of.

    Examples:
        Pysmo types matching instances of
        [`MiniLocationWithDepth`][pysmo.MiniLocationWithDepth] or the class
        itself:

        ```python
        >>> from pysmo.lib.typing import matching_pysmo_types
        >>> from pysmo import MiniLocationWithDepth
        >>>
        >>> mini = MiniLocationWithDepth(latitude=12, longitude=34, depth=56)
        >>> matching_pysmo_types(mini)
        (<class 'pysmo._types._location.Location'>, <class 'pysmo._types._location_with_depth.LocationWithDepth'>)
        >>>
        >>> matching_pysmo_types(MiniLocationWithDepth)
        (<class 'pysmo._types._location.Location'>, <class 'pysmo._types._location_with_depth.LocationWithDepth'>)
        >>>
        ```
    """

    return tuple(proto for proto in get_args(_AnyProto) if isinstance(obj, proto))
