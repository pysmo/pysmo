"""
Defaults for pysmo functions/classes.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum


class SEISMOGRAM_DEFAULTS(Enum):
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time = datetime.fromtimestamp(0, tz=timezone.utc)
    "Seismogram begin time."
    delta = timedelta(seconds=1)
    "Sampling interval."
