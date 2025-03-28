"""
Defaults for various pysmo functions/classes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta


# Seismogram defaults
@dataclass(frozen=True)
class _SEISMOGRAM_DEFAULTS:
    begin_time: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    delta: timedelta = timedelta(seconds=1)


SEISMOGRAM_DEFAULTS = _SEISMOGRAM_DEFAULTS()
