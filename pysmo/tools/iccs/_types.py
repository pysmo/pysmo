from pysmo import Seismogram
from pysmo.lib.validators import datetime_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from typing import Protocol, runtime_checkable
from attrs import define, field, validators
from datetime import datetime, timedelta
import numpy as np
import numpy.typing as npt

__all__ = ["ICCSSeismogram", "MiniICCSSeismogram"]


@runtime_checkable
class ICCSSeismogram(Seismogram, Protocol):
    """Protocol class to define the `ICCSSeismogram` type.

    The `ICCSSeismogram` type extends the [`Seismogram`][pysmo.Seismogram] type
    with the addition of parameters that are required for ICCS.
    """

    @property
    def flip(self) -> bool:
        """Data in seismogram should be flipped for ICCS."""
        ...

    @flip.setter
    def flip(self, value: bool) -> None: ...

    @property
    def select(self) -> bool:
        """Use seismogram to create stack."""
        ...

    @select.setter
    def select(self, value: bool) -> None: ...

    @property
    def t0(self) -> datetime:
        """Initial pick."""
        ...

    @t0.setter
    def t0(self, value: datetime) -> None: ...

    @property
    def t1(self) -> datetime | None:
        """Updated pick."""
        ...

    @t1.setter
    def t1(self, value: datetime | None) -> None: ...


@define(kw_only=True, slots=True)
class MiniICCSSeismogram:
    """Minimal implementation of the [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] type.

    The [`MiniICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] class provides
    a minimal implementation of class that is compatible with the
    [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram].

    Examples:
        Because [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] inherits
        from [`Seismogram`][pysmo.Seismogram], we can easily create
        [`MiniICCSSeismogram`][pysmo.tools.iccs.MiniICCSSeismogram] instances
        from exisiting seismograms using the
        [`clone_to_mini()`][pysmo.functions.clone_to_mini] function, whereby
        the `update` parameter is used to provide the extra information needed:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.iccs import MiniICCSSeismogram
        >>> sac = SAC.from_file("example.sac")
        >>> sac_seis = sac.seismogram
        >>> update = {"t0": sac.timestamps.t0}
        >>> mini_iccs_seis = clone_to_mini(MiniICCSSeismogram, sac_seis, update=update)
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

    t0: datetime = field(validator=datetime_is_utc)
    """Initial pick."""

    t1: datetime | None = field(
        default=None, validator=validators.optional(datetime_is_utc)
    )
    """Updated pick."""

    flip: bool = False
    """Data in seismogram should be flipped for ICCS."""

    select: bool = True
    """Use seismogram to create stack."""

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
