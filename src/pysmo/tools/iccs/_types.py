from collections.abc import Hashable
from enum import StrEnum, auto
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import cmp_using, converters, define, field, setters, validators

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


@define(frozen=True)
class IccsResult:
    """Result of running the ICCS algorithm.

    Returned by [`ICCS.__call__()`][pysmo.tools.iccs.ICCS.__call__].
    """

    convergence: npt.NDArray[np.floating]
    """Convergence criterion value after each iteration."""

    converged: bool
    """Whether the convergence limit was reached before `max_iter` iterations."""


@define(frozen=True)
class McccResult:
    """Result of the MCCC arrival-time refinement step.

    Returned by [`ICCS.run_mccc()`][pysmo.tools.iccs.ICCS.run_mccc]. Every
    list is positional, in the order MCCC processed the seismograms:
    all of `ICCS.seismograms` when `run_mccc(all_seismograms=True)`, otherwise
    only the selected ones in `ICCS.selected_cc_seismograms` order. There is
    no seismogram identity in the result; the caller must line the lists up
    against the same seismogram sequence itself.
    """

    picks: list[pd.Timestamp]
    """Final absolute arrival times for each seismogram."""

    errors: list[pd.Timedelta | None]
    """Per-seismogram timing precision (standard error from covariance
    matrix), or `None` where the underlying system was singular and
    precision could not be estimated at all.
    """

    rmse: pd.Timedelta
    """Root-mean-square error of the inversion fit across the whole array."""

    cc_means: list[float]
    """Per-seismogram mean cross-correlation coefficient (waveform quality)."""

    cc_stds: list[float]
    """Per-seismogram standard deviation of the cross-correlation
    coefficients (waveform consistency)."""


class ConvergenceMethod(StrEnum):
    corrcoef = auto()
    change = auto()


class IccsSeismogram(Seismogram, Protocol):
    """Protocol class to define the `IccsSeismogram` type.

    The `IccsSeismogram` type extends the [`Seismogram`][pysmo.Seismogram] type
    with the addition of parameters that are required for ICCS.
    """

    t0: pd.Timestamp
    """Initial pick."""

    t1: pd.Timestamp | None
    """Updated pick.

    Setting this directly on a seismogram already in an
    [`ICCS`][pysmo.tools.iccs.ICCS] instance's
    [`seismograms`][pysmo.tools.iccs.ICCS.seismograms] list bypasses that
    instance's cache (see the warning there).
    """

    flip: bool
    """Whether the seismogram data should be flipped for ICCS."""

    select: bool
    """Whether to use the seismogram in the stack."""

    extra: dict[Hashable, Any]
    """Extra metadata to store alongside the seismogram."""


@define(kw_only=True)
class MiniIccsSeismogram(SeismogramEndtimeMixin):
    """Minimal implementation of the `IccsSeismogram` type.

    Examples:
        Because [`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] inherits
        from [`Seismogram`][pysmo.Seismogram],
        [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram] instances
        can easily be created from existing seismograms using the
        [`clone_to_mini()`][pysmo.functions.clone_to_mini] function, with the
        `update` parameter providing the extra information needed:

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

    data: npt.NDArray[np.floating] = field(
        factory=lambda: np.array([]),
        converter=convert_to_ndarray,
        validator=validators.instance_of(np.ndarray),
        on_setattr=setters.pipe(setters.convert, setters.validate),
        eq=cmp_using(eq=np.array_equal),
    )
    """Seismogram data."""

    t0: UtcTimestamp = field(
        converter=convert_to_utc_timestamp, on_setattr=setters.convert
    )
    """Initial pick."""

    t1: UtcTimestamp | None = field(
        default=None,
        converter=converters.optional(convert_to_utc_timestamp),
        on_setattr=setters.convert,
    )
    """Updated pick."""

    flip: bool = field(
        default=False,
        converter=bool,
        validator=validators.instance_of(bool),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Whether the seismogram data should be flipped for ICCS."""

    select: bool = field(
        default=True,
        converter=bool,
        validator=validators.instance_of(bool),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Whether to use the seismogram in the stack."""

    extra: dict[Hashable, Any] = field(factory=dict)
    """Extra metadata to store alongside the seismogram."""
