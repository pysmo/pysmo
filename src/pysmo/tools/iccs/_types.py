from pysmo import Seismogram
from pysmo.typing import PositiveTimedelta64
from pysmo.lib.validators import datetime64_is_utc
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from typing import Protocol, runtime_checkable
from beartype import beartype
from attrs import define, field, validators
from enum import StrEnum, auto
import numpy as np

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

    t0: np.datetime64
    """Initial pick as numpy datetime64."""

    t1: np.datetime64 | None
    """Updated pick as numpy datetime64."""

    flip: bool
    """Data in seismogram should be flipped for ICCS."""

    select: bool
    """Use seismogram to create stack."""


@beartype
@define(kw_only=True, slots=True)
class MiniICCSSeismogram(Seismogram):
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
        >>> import numpy as np
        >>> sac = SAC.from_file("example.sac")
        >>> sac_seis = sac.seismogram
        >>> # Use existing pick or set a new one 10 seconds after begin time
        >>> update = {"t0": sac.timestamps.t0 or sac_seis.begin_time + np.timedelta64(10_000_000, 'us')}
        >>> mini_iccs_seis = clone_to_mini(MiniICCSSeismogram, sac_seis, update=update)
        >>>
        ```
    """

    begin_time: np.datetime64 = field(
        default=SEISMOGRAM_DEFAULTS.begin_time.value, validator=datetime64_is_utc
    )
    """Seismogram begin time as numpy datetime64."""

    delta: PositiveTimedelta64 = SEISMOGRAM_DEFAULTS.delta.value
    """Seismogram sampling interval as numpy timedelta64."""

    data: np.ndarray = field(factory=lambda: np.array([]))
    """Seismogram data."""

    t0: np.datetime64 = field(validator=datetime64_is_utc)
    """Initial pick as numpy datetime64."""

    t1: np.datetime64 | None = field(
        default=None, validator=validators.optional(datetime64_is_utc)
    )
    """Updated pick as numpy datetime64."""

    flip: bool = False
    """Data in seismogram should be flipped for ICCS."""

    select: bool = True
    """Use seismogram to create stack."""
