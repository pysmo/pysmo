import numpy as np
from pysmo import Seismogram
from pysmo._types._seismogram import SeismogramEndtimeMixin
from pysmo.typing import PositiveTimedelta
from pysmo.lib.validators import datetime_is_utc
from pysmo.lib.defaults import SeismogramDefaults
from collections.abc import Hashable
from typing import Protocol, Any, runtime_checkable
from beartype import beartype
from attrs import define, field, validators
from pandas import Timestamp
from enum import StrEnum, auto

__all__ = ["ICCSSeismogram", "MiniICCSSeismogram"]


class ConvergenceMethod(StrEnum):
    corrcoef = auto()
    change = auto()


@runtime_checkable
class ICCSSeismogram(Seismogram, Protocol):
    """Protocol class to define the `ICCSSeismogram` type.

    The `ICCSSeismogram` type extends the [`Seismogram`][pysmo.Seismogram] type
    with the addition of parameters that are required for ICCS.
    """

    t0: Timestamp
    """Initial pick."""

    t1: Timestamp | None
    """Updated pick."""

    flip: bool
    """Data in seismogram should be flipped for ICCS."""

    select: bool
    """Use seismogram to create stack."""

    extra: dict[Hashable, Any]
    """Extra metadata that may be helpful to be stored alongside the seismogram."""


@define(kw_only=True, slots=True)
@beartype
class MiniICCSSeismogram(SeismogramEndtimeMixin, ICCSSeismogram):
    """Minimal implementation of the [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] type.

    The [`MiniICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] class provides
    a minimal implementation of a class that is compatible with the
    [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] protocol.

    Examples:
        Because [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] inherits
        from [`Seismogram`][pysmo.Seismogram], we can easily create
        [`MiniICCSSeismogram`][pysmo.tools.iccs.MiniICCSSeismogram] instances
        from existing seismograms using the
        [`clone_to_mini()`][pysmo.functions.clone_to_mini] function, whereby
        the `update` parameter is used to provide the extra information needed:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.iccs import MiniICCSSeismogram
        >>> from pandas import Timedelta
        >>> sac = SAC.from_file("example.sac")
        >>> sac_seis = sac.seismogram
        >>> # Use existing pick or set a new one 10 seconds after begin time
        >>> update = {"t0": sac.timestamps.t0 or sac_seis.begin_time + Timedelta(seconds=10)}
        >>> mini_iccs_seis = clone_to_mini(MiniICCSSeismogram, sac_seis, update=update)
        >>>
        ```
    """

    begin_time: Timestamp = field(
        default=SeismogramDefaults.begin_time, validator=datetime_is_utc
    )
    """Seismogram begin time."""

    delta: PositiveTimedelta = SeismogramDefaults.delta
    """Seismogram sampling interval."""

    data: np.ndarray = field(factory=lambda: np.array([]))
    """Seismogram data."""

    t0: Timestamp = field(validator=datetime_is_utc)
    """Initial pick."""

    t1: Timestamp | None = field(
        default=None, validator=validators.optional(datetime_is_utc)
    )
    """Updated pick."""

    flip: bool = False
    """Data in seismogram should be flipped for ICCS."""

    select: bool = True
    """Use seismogram to create stack."""

    extra: dict[Hashable, Any] = field(factory=dict)
    """Extra metadata that may be helpful to be stored alongside the seismogram."""
