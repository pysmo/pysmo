from ._location_with_depth import LocationWithDepth
from pysmo.lib.validators import datetime_is_utc
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from datetime import datetime

__all__ = ["Event", "MiniEvent"]


@runtime_checkable
class Event(LocationWithDepth, Protocol):
    """Protocol class to define the `Event` type."""

    @property
    def time(self) -> datetime:
        """Event origin time."""
        ...

    @time.setter
    def time(self, value: datetime) -> None: ...


@define(kw_only=True, slots=True)
class MiniEvent:
    """Minimal class for use with the [`Event`][pysmo.Event] type.

    The `MiniEvent` class provides a minimal implementation of class that is
    compatible with the [`Event`][pysmo.Event] type.

    Examples:
        ```python
        >>> from pysmo import MiniEvent, Event, LocationWithDepth, Location
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> my_event = MiniEvent(latitude=-24.68, longitude=-26.73, depth=15234.0, time=now)
        >>> isinstance(my_event, Event)
        True
        >>> isinstance(my_event, Location)
        True
        >>> isinstance(my_event, LocationWithDepth)
        True
        >>>
        ```
    """

    time: datetime = field(validator=datetime_is_utc)
    """Event origin time."""

    latitude: float = field(validator=[validators.ge(-90), validators.le(90)])
    """Event atitude from -90 to 90 degrees."""

    longitude: float = field(validator=[validators.gt(-180), validators.le(180)])
    """Event longitude from -180 to 180 degrees."""

    depth: float
    """Event depth in metres."""
