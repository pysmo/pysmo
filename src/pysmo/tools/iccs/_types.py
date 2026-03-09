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

__all__ = ["IccsResult", "IccsSeismogram", "McccResult", "MiniIccsSeismogram"]


@define(frozen=True, slots=True)
class IccsResult:
    """Result returned by [`ICCS.__call__()`][pysmo.tools.iccs.ICCS.__call__]."""

    convergence: np.ndarray
    """Convergence criterion value after each iteration."""

    converged: bool
    """Whether the convergence limit was reached before `max_iter` iterations."""


@define(frozen=True, slots=True)
class McccResult:
    """Result returned by [`ICCS.run_mccc()`][pysmo.tools.iccs.ICCS.run_mccc].

    These results include all seismograms if `run_mccc()` is called with
    `all_seismograms=True`, only the selected ones otherwise.
    """

    picks: list[pd.Timestamp]
    """Final absolute arrival times for each seismogram."""

    errors: list[pd.Timedelta]
    """Per-seismogram timing precision (standard error from covariance matrix)."""

    rmse: pd.Timedelta
    """Root-mean-square error of the inversion fit across the whole array."""

    cc_means: list[float]
    """Per-seismogram mean cross-correlation coefficient (waveform quality)."""

    cc_errs: list[float]
    """Per-seismogram standard deviation of cross-correlation coefficients (waveform consistency)."""


class ConvergenceMethod(StrEnum):
    corrcoef = auto()
    change = auto()


@runtime_checkable
class IccsSeismogram(Seismogram, Protocol):
    """Protocol class to define the `IccsSeismogram` type.

    The `IccsSeismogram` type extends the [`Seismogram`][pysmo.Seismogram] type
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
class MiniIccsSeismogram(SeismogramEndtimeMixin, IccsSeismogram):
    """Minimal implementation of the [`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] type.

    The [`MiniIccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] class provides
    a minimal implementation of a class that is compatible with the
    [`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] protocol.

    Examples:
        Because [`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] inherits
        from [`Seismogram`][pysmo.Seismogram], we can easily create
        [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram] instances
        from existing seismograms using the
        [`clone_to_mini()`][pysmo.functions.clone_to_mini] function, whereby
        the `update` parameter is used to provide the extra information needed:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.iccs import MiniIccsSeismogram
        >>> import pandas as pd
        >>> sac = SAC.from_file("example.sac")
        >>> sac_seis = sac.seismogram
        >>> # Use existing pick or set a new one 10 seconds after begin time
        >>> update = {"t0": sac_seis.begin_time + pd.Timedelta(seconds=10) if pd.isnull(sac.timestamps.t0) else sac.timestamps.t0}
        >>> mini_iccs_seis = clone_to_mini(MiniIccsSeismogram, sac_seis, update=update)
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
