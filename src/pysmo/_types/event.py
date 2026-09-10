from typing import Protocol

import pandas as pd
from attrs import define, field, setters

from pysmo.lib.converters import to_longitude, to_utc_timestamp
from pysmo.lib.validators import is_latitude, is_longitude
from pysmo.typing import UtcTimestamp

from .location_with_depth import LocationWithDepth

__all__ = ["Event", "MiniEvent"]


class Event(LocationWithDepth, Protocol):
    """Protocol class to define the `Event` type.

    A seismic event: a hypocentre from
    [`LocationWithDepth`][pysmo.LocationWithDepth] together with an origin
    time.
    """

    time: pd.Timestamp
    """Event origin time."""


@define(kw_only=True)
class MiniEvent:
    """Minimal implementation of the `Event` type.

    See [`Event`][pysmo.Event].

    Examples:
        ```python
        >>> from pysmo import MiniEvent
        >>> import pandas as pd
        >>> from datetime import timezone
        >>> now = pd.Timestamp.now(timezone.utc)
        >>> event = MiniEvent(latitude=-24.68, longitude=-26.73, depth=15234.0, time=now)
        >>>
        ```
    """

    time: UtcTimestamp = field(
        converter=to_utc_timestamp,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event origin time."""

    latitude: float = field(
        converter=float,
        validator=is_latitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event latitude from -90 to 90 degrees."""

    longitude: float = field(
        converter=to_longitude,
        validator=is_longitude,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Event longitude from -180 to 180 degrees (-180 is stored as +180)."""

    depth: float = field(
        converter=float, on_setattr=setters.pipe(setters.convert, setters.validate)
    )
    """Event depth in metres, positive downwards."""
