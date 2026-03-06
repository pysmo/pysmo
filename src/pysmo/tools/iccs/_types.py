from collections.abc import Hashable
from enum import StrEnum, auto
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd
from attrs import define, field, setters, validators

from pysmo import Seismogram
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)
from pysmo.typing import PositiveTimedelta, UtcTimestamp

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

    t0: pd.Timestamp
    """Initial pick."""

    t1: pd.Timestamp | None
    """Updated pick."""

    flip: bool
    """Data in seismogram should be flipped for ICCS."""

    select: bool
    """Use seismogram to create stack."""

    extra: dict[Hashable, Any]
    """Extra metadata that may be helpful to be stored alongside the seismogram."""


@define(kw_only=True, slots=True)
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
        >>> import pandas as pd
        >>> sac = SAC.from_file("example.sac")
        >>> sac_seis = sac.seismogram
        >>> # Use existing pick or set a new one 10 seconds after begin time
        >>> update = {"t0": sac.timestamps.t0 or sac_seis.begin_time + pd.Timedelta(seconds=10)}
        >>> mini_iccs_seis = clone_to_mini(MiniICCSSeismogram, sac_seis, update=update)
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

    t0: UtcTimestamp = field(
        converter=convert_to_utc_timestamp, on_setattr=setters.convert
    )
    """Initial pick."""

    t1: UtcTimestamp | None = field(
        default=None, converter=convert_to_utc_timestamp, on_setattr=setters.convert
    )
    """Updated pick."""

    flip: bool = field(
        default=False,
        converter=bool,
        validator=validators.instance_of(bool),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Data in seismogram should be flipped for ICCS."""

    select: bool = field(
        default=True,
        converter=bool,
        validator=validators.instance_of(bool),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Use seismogram to create stack."""

    extra: dict[Hashable, Any] = field(factory=dict)
    """Extra metadata that may be helpful to be stored alongside the seismogram."""
