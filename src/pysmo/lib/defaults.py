"""
Defaults for pysmo functions/classes.
"""

import pandas as pd
from datetime import timezone
from dataclasses import dataclass


@dataclass(frozen=True)
class _SeismogramDefaults:
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time: pd.Timestamp = pd.Timestamp.fromtimestamp(0, tz=timezone.utc)
    "Seismogram begin time."

    delta: pd.Timedelta = pd.Timedelta(seconds=1)
    "Sampling interval."


SeismogramDefaults = _SeismogramDefaults()
