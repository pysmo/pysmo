from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd
from attrs import define, field, setters, validators

from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)
from pysmo.typing import PositiveTimedelta, UtcTimestamp

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

    begin_time: pd.Timestamp
    """Seismogram begin time."""

    data: np.ndarray
    """Seismogram data."""

    delta: pd.Timedelta
    """The sampling interval.

    Should be a positive `pd.Timedelta` instance.
    """

    @property
    def end_time(self) -> pd.Timestamp:
        """Seismogram end time."""
        ...


# --8<-- [end:seismogram-protocol]


# --8<-- [start:seismogram-mixin]
class SeismogramEndtimeMixin:
    """Mixin class to add `end_time` property to a `Seismogram` object."""

    @property
    def end_time(self: Seismogram) -> pd.Timestamp:
        """Seismogram end time."""
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)


# --8<-- [end:seismogram-mixin]


# --8<-- [start:mini-seismogram]


@define(kw_only=True, slots=True)
class MiniSeismogram(SeismogramEndtimeMixin):
    """Minimal class for use with the [`Seismogram`][pysmo.Seismogram] type.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Examples:
        ```python
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> import pandas as pd
        >>> from datetime import timezone
        >>> import numpy as np
        >>> now = pd.Timestamp.now(timezone.utc)
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> seismogram = MiniSeismogram(begin_time=now, delta=delta, data=np.random.rand(100))
        >>> isinstance(seismogram, Seismogram)
        True
        >>>
        ```
    """

    begin_time: UtcTimestamp = field(
        default=SeismogramDefaults.begin_time,
        converter=convert_to_utc_timestamp,
        on_setattr=setters.convert,
    )
    """Seismogram begin time."""

    delta: PositiveTimedelta = field(
        default=SeismogramDefaults.delta,
        converter=convert_to_timedelta,
        validator=[
            validators.instance_of(pd.Timedelta),
            validators.gt(pd.Timedelta(0)),
        ],
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Seismogram sampling interval."""

    data: np.ndarray = field(
        factory=lambda: np.array([]),
        converter=convert_to_ndarray,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Seismogram data."""


# --8<-- [end:mini-seismogram]
