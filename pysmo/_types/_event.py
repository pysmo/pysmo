from pysmo._types._hypocenter import Hypocenter, MiniHypocenter
from pysmo._lib.utils import datetime_is_utc
from typing import Protocol, runtime_checkable
from attrs import define, field
from attrs_strict import type_validator
from datetime import datetime

__all__ = ["Event", "MiniEvent"]


@runtime_checkable
class Event(Hypocenter, Protocol):
    """Protocol class to define the `Event` type."""

    @property
    def time(self) -> datetime:
        """Event origin time."""
        ...

    @time.setter
    def time(self, value: datetime) -> None: ...


@define(kw_only=True)
class MiniEvent(MiniHypocenter):
    """Minimal class for use with the [`Event`][pysmo.Event] type.

    The `MiniEvent` class provides a minimal implementation of class that is
    compatible with the [`Event`][pysmo.Event] type. The class is a
    subclass of [`MiniHypocenter`][pysmo.MiniHypocenter], and
    therefore also matches the [`Location`][pysmo.Location] and
    [`Hypocenter`][pysmo.Hypocenter] types.

    Examples:
        >>> from pysmo import MiniEvent, Event, Hypocenter, Location
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> my_event = MiniEvent(latitude=-24.68, longitude=-26.73,
                                 depth=15234.0, time=now)
        >>> isinstance(my_event, Event)
        True
        >>> isinstance(my_event, Hypocenter)
        True
        >>> isinstance(my_event, Location)
        True
    """

    time: datetime = field(validator=[type_validator(), datetime_is_utc])
    """Event origin time."""
