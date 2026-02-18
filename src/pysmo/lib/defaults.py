"""
Defaults for pysmo functions/classes.
"""

import numpy as np
from enum import Enum


class SEISMOGRAM_DEFAULTS(Enum):
    """Defaults for classes related to [`Seismogram`][pysmo.Seismogram]."""

    begin_time = np.datetime64(0, "us")
    "Seismogram begin time (epoch start in microsecond precision)."
    delta = np.timedelta64(1_000_000, "us")  # 1 second in microseconds
    "Sampling interval (1 second)."
