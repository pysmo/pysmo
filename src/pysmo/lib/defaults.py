"""Default values for pysmo's functions and classes."""

from dataclasses import dataclass
from datetime import UTC

import pandas as pd


@dataclass(frozen=True)
class _SeismogramDefaults:
    """Defaults for `Seismogram`-related classes.

    See [`Seismogram`][pysmo.Seismogram].
    """

    begin_time: pd.Timestamp = pd.Timestamp.fromtimestamp(0, tz=UTC)
    "Seismogram begin time."

    delta: pd.Timedelta = pd.Timedelta(seconds=1)
    "Sampling interval."


SeismogramDefaults = _SeismogramDefaults()
