from pysmo.lib.validators import datetime_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from typing import Protocol, runtime_checkable
from attrs import define, field
from datetime import datetime, timedelta
import numpy as np
import numpy.typing as npt

__all__ = ["Seismogram", "MiniSeismogram"]


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

    def __len__(self) -> int:
        """The length of the Seismogram.

        Returns:
            Number of samples in the data array.
        """
        ...

    @property
    def data(self) -> npt.NDArray:
        """Seismogram data."""
        ...

    @data.setter
    def data(self, value: npt.NDArray) -> None: ...

    @property
    def begin_time(self) -> datetime:
        """Seismogram begin time."""
        ...

    @begin_time.setter
    def begin_time(self, value: datetime) -> None: ...

    @property
    def end_time(self) -> datetime:
        """Seismogram end time."""
        ...

    @property
    def delta(self) -> timedelta:
        """The sampling interval."""
        ...

    @delta.setter
    def delta(self, value: timedelta) -> None: ...


@define(kw_only=True, slots=True)
class MiniSeismogram:
    """Minimal class for use with the [`Seismogram`][pysmo.Seismogram] type.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Examples:
        ```python
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime, timedelta, timezone
        >>> import numpy as np
        >>> now = datetime.now(timezone.utc)
        >>> delta = timedelta(seconds=0.1)
        >>> seismogram = MiniSeismogram(begin_time=now, delta=delta, data=np.random.rand(100))
        >>> isinstance(seismogram, Seismogram)
        True
        >>>
        ```
    """

    begin_time: datetime = field(
        default=SEISMOGRAM_DEFAULTS.begin_time.value, validator=datetime_is_utc
    )
    """Seismogram begin time."""

    delta: timedelta = SEISMOGRAM_DEFAULTS.delta.value
    """Seismogram sampling interval."""

    data: npt.NDArray = field(factory=lambda: np.array([]))
    """Seismogram data."""

    def __len__(self) -> int:
        """The length of the Seismogram.

        Returns:
            Number of samples in the data array.
        """
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        """Seismogram end time."""
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self) - 1)
