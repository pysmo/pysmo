from pysmo.lib.validators import timestamp_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.typing import PositiveTimedelta
from typing import Protocol, runtime_checkable
from attrs import define, field
import pandas as pd
import numpy as np
from beartype import beartype

__all__ = ["Seismogram", "MiniSeismogram"]


# --8<-- [start:seismogram-protocol]


@runtime_checkable
class Seismogram(Protocol):
    """Protocol class to define the `Seismogram` type.

    Examples:
        Usage for a function that takes a Seismogram compatible class instance as
        argument and returns the begin time as string:

        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC  # SAC is a class that "speaks" Seismogram
        >>>
        >>> def example_function(seis_in: Seismogram) -> str:
        ...     return str(seis_in.begin_time)
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> seismogram = sac.seismogram
        >>> example_function(seismogram)
        '2005-03-01 07:23:02.160000+00:00'
        >>>
        ```
    """

    begin_time: pd.Timestamp
    """Seismogram begin time as pandas Timestamp with UTC timezone."""

    data: np.ndarray
    """Seismogram data."""

    delta: pd.Timedelta
    """The sampling interval as pandas Timedelta.

    Should be a positive Timedelta value.
    """

    def __len__(self) -> int:
        """The length of the Seismogram.

        Returns:
            Number of samples in the data array.
        """
        return len(self.data)

    @property
    def end_time(self) -> pd.Timestamp:
        """Seismogram end time as pandas Timestamp with UTC timezone."""
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self) - 1)


# --8<-- [end:seismogram-protocol]
# --8<-- [start:mini-seismogram]


@beartype
@define(kw_only=True, slots=True)
class MiniSeismogram(Seismogram):
    """Minimal class for use with the [`Seismogram`][pysmo.Seismogram] type.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Examples:
        ```python
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> import pandas as pd
        >>> now = pd.Timestamp('2020-01-01T12:00:00', tz='UTC')
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> seismogram = MiniSeismogram(begin_time=now, delta=delta, data=np.random.rand(100))
        >>> isinstance(seismogram, Seismogram)
        True
        >>>
        ```
    """

    begin_time: pd.Timestamp = field(
        default=SEISMOGRAM_DEFAULTS.begin_time.value, validator=timestamp_is_utc
    )
    """Seismogram begin time as pandas Timestamp with UTC timezone."""

    delta: PositiveTimedelta = SEISMOGRAM_DEFAULTS.delta.value
    """Seismogram sampling interval as pandas Timedelta."""

    data: np.ndarray = field(factory=lambda: np.array([]))
    """Seismogram data."""


# --8<-- [end:mini-seismogram]
