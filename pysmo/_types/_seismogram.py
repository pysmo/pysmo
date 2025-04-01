from pysmo.lib.validators import datetime_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from typing import Protocol, runtime_checkable
from attrs import define, field
from attrs_strict import type_validator
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

        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC  # SAC is a class that "speaks" Seismogram
        >>> def example_function(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> my_seismogram = my_sac.seismogram
        >>> example_function(my_seismogram)
        '2005-03-02T07:23:02.160000'
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
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime, timedelta, timezone
        >>> import numpy as np
        >>> now = datetime.now(timezone.utc)
        >>> delta0 = timedelta(seconds=0.1)
        >>> my_seismogram = MiniSeismogram(begin_time=now, delta=delta,
                                           data=np.random.rand(100))
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = field(
        default=SEISMOGRAM_DEFAULTS.begin_time.value,
        validator=[type_validator(), datetime_is_utc],
    )
    """Seismogram begin time."""

    delta: timedelta = field(
        default=SEISMOGRAM_DEFAULTS.delta.value,
        validator=type_validator(),
    )
    """Seismogram sampling interval."""

    data: npt.NDArray = field(factory=lambda: np.array([]), validator=type_validator())
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
