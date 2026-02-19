"""
Defaults for pysmo functions/classes.
"""

from pandas import Timestamp, Timedelta
from datetime import timezone
from enum import Enum


class SEISMOGRAM_DEFAULTS(Enum):
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time = Timestamp.fromtimestamp(0, tz=timezone.utc)
    "Seismogram begin time."
    delta = Timedelta(seconds=1)
    "Sampling interval."
