"""
Defaults for various pysmo functions/classes.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class _SEISMOGRAM_DEFAULTS:
    begin_time: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    sampling_rate: float = 1


SEISMOGRAM_DEFAULTS = _SEISMOGRAM_DEFAULTS()
