from ._location_with_depth import LocationWithDepth
from pysmo.lib.validators import timestamp_is_utc
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
import pandas as pd

__all__ = ["Event", "MiniEvent"]


@runtime_checkable
class Event(LocationWithDepth, Protocol):
    """Protocol class to define the `Event` type."""

    time: pd.Timestamp
    """Event origin time as pandas Timestamp with UTC timezone."""


@define(kw_only=True, slots=True)
class MiniEvent:
    """Minimal class for use with the [`Event`][pysmo.Event] type.

    The `MiniEvent` class provides a minimal implementation of class that is
    compatible with the [`Event`][pysmo.Event] type.

    Examples:
        ```python
        >>> from pysmo import MiniEvent, Event, LocationWithDepth, Location
        >>> import pandas as pd
        >>> now = pd.Timestamp('2020-01-01T12:00:00', tz='UTC')
        >>> event = MiniEvent(latitude=-24.68, longitude=-26.73, depth=15234.0, time=now)
        >>> isinstance(event, Event)
        True
        >>> isinstance(event, Location)
        True
        >>> isinstance(event, LocationWithDepth)
        True
        >>>
        ```
    """

    time: pd.Timestamp = field(validator=timestamp_is_utc)
    """Event origin time as pandas Timestamp with UTC timezone."""

    latitude: float = field(validator=[validators.ge(-90), validators.le(90)])
    """Event latitude from -90 to 90 degrees."""

    longitude: float = field(validator=[validators.gt(-180), validators.le(180)])
    """Event longitude from -180 to 180 degrees."""

    depth: float
    """Event depth in metres."""
