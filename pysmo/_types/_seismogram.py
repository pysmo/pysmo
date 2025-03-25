from pysmo._lib.utils import datetime_is_utc
from pysmo._lib.defaults import SEISMOGRAM_DEFAULTS
from typing import Self, Protocol, runtime_checkable
from attrs import define, field
from attrs_strict import type_validator
from datetime import datetime, timedelta
from copy import copy
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
    def delta(self) -> float:
        """The sampling interval [s]."""
        ...

    @delta.setter
    def delta(self, value: float) -> None: ...


@define(kw_only=True)
class MiniSeismogram:
    """Minimal class for use with the [`Seismogram`][pysmo.Seismogram] type.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Examples:
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime, timezone
        >>> import numpy as np
        >>> now = datetime.now(timezone.utc)
        >>> my_seismogram = MiniSeismogram(begin_time=now, delta=0.1,
                                           data=np.random.rand(100), id='myseis')
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = field(
        default=SEISMOGRAM_DEFAULTS.begin_time,
        validator=[type_validator(), datetime_is_utc],
    )
    """Seismogram begin time."""

    delta: float | int = field(
        default=SEISMOGRAM_DEFAULTS.delta,
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
        return self.begin_time + timedelta(seconds=self.delta * (len(self) - 1))

    @classmethod
    def clone(cls, seismogram: Seismogram, skip_data: bool = False) -> Self:
        """Create a new MiniSeismogram instance from an existing
        [Seismogram][pysmo.Seismogram] object.

        Parameters:
            seismogram: The Seismogram to be cloned.
            skip_data: Create clone witout copying data.

        Returns:
            A copy of the original Seismogram object.

        Examples:
            Create a copy of a [SAC][pysmo.classes.SAC] object without data:

            >>> from pysmo import MiniSeismogram
            >>> from pysmo.classes import SAC
            >>> original_seis = SAC.from_file('testfile.sac').seismogram
            >>> cloned_seis = MiniSeismogram.clone(original_seis, skip_data=True)
            >>> print(cloned_seis.data)
            []

            Create a copy of a [SAC][pysmo.classes.SAC] object with data:

            >>> from pysmo import MiniSeismogram
            >>> from pysmo.classes import SAC
            >>> from numpy.testing import assert_allclose
            >>> original_seis = SAC.from_file('testfile.sac').seismogram
            >>> cloned_seis = MiniSeismogram.clone(original_seis)
            >>> assert_allclose(original_seis.data, cloned_seis.data)
            True
            >>> print(cloned_seis.data)
            [2302. 2313. 2345. ... 2836. 2772. 2723.]
        """
        cloned_seismogram = cls()
        cloned_seismogram.begin_time = copy(seismogram.begin_time)
        cloned_seismogram.delta = seismogram.delta
        if not skip_data:
            cloned_seismogram.data = copy(seismogram.data)
        return cloned_seismogram
