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
    """The `Seismogram` class defines a type for a basic seismogram as used in pysmo.

    Attributes:
        __len__: The length of the Seismogram.
        data: Seismogram data.
        delta: The sampling interval [s].
        begin_time: Seismogram begin time.
        end_time: Seismogram end time (read only).

    Examples:
        Usage for a function that takes a Seismogram compatible class instance as
        argument and returns the begin time in isoformat:

        >>> from pysmo import SAC, Seismogram  # SAC is a class that "speaks" Seismogram
        >>> def begin_time_in_isoformat(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> my_seismogram = my_sac.seismogram
        >>> example_function(my_seismogram)
        '2005-03-02T07:23:02.160000'
    """

    def __len__(self) -> int: ...

    @property
    def data(self) -> npt.NDArray: ...

    @data.setter
    def data(self, value: npt.NDArray) -> None: ...

    @property
    def begin_time(self) -> datetime: ...

    @begin_time.setter
    def begin_time(self, value: datetime) -> None: ...

    @property
    def end_time(self) -> datetime: ...

    @property
    def delta(self) -> float: ...

    @delta.setter
    def delta(self, value: float) -> None: ...


@define(kw_only=True)
class MiniSeismogram:
    """Minimal class for seismogram data.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.Seismogram] type.

    Attributes:
        begin_time: Seismogram begin time.
        end_time: Seismogram end time.
        delta: Seismogram sampling interval.
        data: Seismogram data.

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
    delta: float | int = field(
        default=SEISMOGRAM_DEFAULTS.delta,
        validator=type_validator(),
    )
    data: npt.NDArray = field(factory=lambda: np.array([]), validator=type_validator())

    def __len__(self) -> int:
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + timedelta(seconds=self.delta * (len(self) - 1))

    @classmethod
    def clone(cls, seismogram: Seismogram, skip_data: bool = False) -> Self:
        """Create a new MiniSeismogram instance from an existing
        [Seismogram][pysmo.types.Seismogram] object.

        Attributes:
            seismogram: The Seismogram to be cloned.
            skip_data: Create clone witout copying data.

        Returns:
            A copy of the original Seismogram object.

        Examples:
            Create a copy of a [SAC][pysmo.classes.sac.SAC] object without data:

            >>> from pysmo import SAC, MiniSeismogram
            >>> original_seis = SAC.from_file('testfile.sac').seismogram
            >>> cloned_seis = MiniSeismogram.clone(original_seis, skip_data=True)
            >>> print(cloned_seis.data)
            []

            Create a copy of a [SAC][pysmo.classes.sac.SAC] object with data:

            >>> from pysmo import SAC, MiniSeismogram
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
