"""
Defaults for pysmo functions/classes.
"""

from pandas import Timestamp, Timedelta
from datetime import timezone
from dataclasses import dataclass


@dataclass(frozen=True)
class _SeismogramDefaults:
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time: Timestamp = Timestamp.fromtimestamp(0, tz=timezone.utc)
    "Seismogram begin time."

    delta: Timedelta = Timedelta(seconds=1)
    "Sampling interval."


SeismogramDefaults = _SeismogramDefaults()
