from .location_with_depth import LocationWithDepth
from pysmo.typing import UtcTimestamp
from pysmo.lib.validators import convert_to_utc_timestamp
from typing import Protocol, runtime_checkable
from attrs import define, field, validators, setters
import pandas as pd

__all__ = ["Event", "MiniEvent"]


@runtime_checkable
class Event(LocationWithDepth, Protocol):
    """Protocol class to define the `Event` type."""

    time: pd.Timestamp
    """Event origin time."""


@define(kw_only=True, slots=True)
class MiniEvent:
    """Minimal class for use with the [`Event`][pysmo.Event] type.

    The `MiniEvent` class provides a minimal implementation of class that is
    compatible with the [`Event`][pysmo.Event] type.

    Examples:
        ```python
        >>> from pysmo import MiniEvent, Event, LocationWithDepth, Location
        >>> import pandas as pd
        >>> from datetime import timezone
        >>> now = pd.Timestamp.now(timezone.utc)
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

    time: UtcTimestamp = field(
        converter=convert_to_utc_timestamp,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event origin time."""

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=float,
        validator=[validators.gt(-180), validators.le(180)],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event longitude from -180 to 180 degrees."""

    depth: float = field(
        converter=float, on_setattr=setters.pipe(setters.convert, setters.validate)
    )
    """Event depth in metres."""
