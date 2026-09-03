from typing import Protocol

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import cmp_using, define, field, setters, validators

from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)
from pysmo.typing import PositiveTimedelta, UtcTimestamp

__all__ = ["MiniSeismogram", "Seismogram"]


# --8<-- [start:seismogram-protocol]


class Seismogram(Protocol):
    """Protocol class to define the `Seismogram` type.

    Examples:
        A function annotated with `Seismogram` accepts any compatible class.
        This one returns the begin time in ISO format:

        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC  # SAC implements the Seismogram protocol
        >>>
        >>> def example_function(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> seismogram = sac.seismogram
        >>> example_function(seismogram)
        '2010-02-27T06:44:06.069538+00:00'
        >>>
        ```
    """

    begin_time: pd.Timestamp
    """Seismogram begin time."""

    data: npt.NDArray[np.floating]
    """Seismogram data."""

    delta: pd.Timedelta
    """Seismogram sampling interval.

    Must be a positive `pd.Timedelta`.
    """

    @property
    def end_time(self) -> pd.Timestamp:
        """Seismogram end time."""
        ...


# --8<-- [end:seismogram-protocol]


# --8<-- [start:seismogram-mixin]
class SeismogramEndtimeMixin:
    """Add a computed `end_time` property.

    Mix into any class that provides `begin_time`, `delta`, and `data`.
    """

    __slots__ = ()

    @property
    def end_time(self: Seismogram) -> pd.Timestamp:
        """Seismogram end time."""
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)


# --8<-- [end:seismogram-mixin]


# --8<-- [start:mini-seismogram]


@define(kw_only=True)
class MiniSeismogram(SeismogramEndtimeMixin):
    """Minimal implementation of the `Seismogram` type.

    See [`Seismogram`][pysmo.Seismogram].

    Examples:
        ```python
        >>> from pysmo import MiniSeismogram
        >>> import pandas as pd
        >>> from datetime import timezone
        >>> import numpy as np
        >>> now = pd.Timestamp.now(timezone.utc)
        >>> delta = pd.Timedelta(seconds=0.1)
        >>> seismogram = MiniSeismogram(
        ...     begin_time=now, delta=delta, data=np.random.rand(100)
        ... )
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

    data: npt.NDArray[np.floating] = field(
        factory=lambda: np.array([]),
        converter=convert_to_ndarray,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
        eq=cmp_using(eq=np.array_equal),
    )
    """Seismogram data."""


# --8<-- [end:mini-seismogram]
