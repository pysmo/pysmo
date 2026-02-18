"""
Defaults for pysmo functions/classes.
"""

import pandas as pd
from enum import Enum


class SEISMOGRAM_DEFAULTS(Enum):
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time = pd.Timestamp(0, tz="UTC")
    "Seismogram begin time (epoch start with UTC timezone)."
    delta = pd.Timedelta(seconds=1)
    "Sampling interval (1 second)."
