import numpy as np
from pysmo.lib.validators import datetime_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.typing import PositiveTimedelta
from typing import Protocol, runtime_checkable
from attrs import define, field
from pandas import Timestamp, Timedelta
from beartype import beartype

__all__ = ["Seismogram", "MiniSeismogram"]


# --8<-- [start:seismogram-protocol]


@runtime_checkable
class Seismogram(Protocol):
    """Protocol class to define the `Seismogram` type.

    Examples:
        Usage for a function that takes a Seismogram compatible class instance as
        argument and returns the begin time in isoformat:

        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC  # SAC is a class that "speaks" Seismogram
        >>>
        >>> def example_function(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> seismogram = sac.seismogram
        >>> example_function(seismogram)
        '2005-03-01T07:23:02.160000+00:00'
        >>>
        ```
    """

    begin_time: Timestamp
    """Seismogram begin time."""

    data: np.ndarray
    """Seismogram data."""

    delta: Timedelta
    """The sampling interval.

    Should be a positive `Timedelta` instance.
    """

    @property
    def end_time(self) -> Timestamp:
        """Seismogram end time."""
        ...


# --8<-- [end:seismogram-protocol]


# --8<-- [start:seismogram-mixin]
class SeismogramEndtimeMixin:
    """Mixin class to add `end_time` property to a `Seismogram` object."""

    @property
    def end_time(self: Seismogram) -> Timestamp:
        """Seismogram end time."""
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)


# --8<-- [end:seismogram-mixin]


# --8<-- [start:mini-seismogram]


@beartype
@define(kw_only=True, slots=True)
class MiniSeismogram(SeismogramEndtimeMixin):
    """Minimal class for use with the [`Seismogram`][pysmo.Seismogram] type.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Examples:
        ```python
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from pandas import Timestamp, Timedelta
        >>> from datetime import timezone
        >>> import numpy as np
        >>> now = Timestamp.now(timezone.utc)
        >>> delta = Timedelta(seconds=0.1)
        >>> seismogram = MiniSeismogram(begin_time=now, delta=delta, data=np.random.rand(100))
        >>> isinstance(seismogram, Seismogram)
        True
        >>>
        ```
    """

    begin_time: Timestamp = field(
        default=SEISMOGRAM_DEFAULTS.begin_time.value, validator=datetime_is_utc
    )
    """Seismogram begin time."""

    delta: PositiveTimedelta = SEISMOGRAM_DEFAULTS.delta.value
    """Seismogram sampling interval."""

    data: np.ndarray = field(factory=lambda: np.array([]))
    """Seismogram data."""


# --8<-- [end:mini-seismogram]
