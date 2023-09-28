"""
Defaults for various pysmo functions/classes.
"""
from dataclasses import dataclass
from datetime import datetime, timezone


# Default model for distance and azimuth calculations
DEFAULT_ELLPS = "WGS84"


# SacIO defaults
@dataclass(frozen=True)
class _SACIO_DEFAULTS:
    b: float = 0
    delta: float = 1
    nvhdr: int = 7
    iftype: str = "time"
    idep: str = "unkn"
    iztype: str = "unkn"
    ievtyp: str = "unkn"
    leven: bool = True


# Seismogram defaults
@dataclass(frozen=True)
class _SEISMOGRAM_DEFAULTS:
    begin_time: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    delta: float = 1


SACIO_DEFAULTS = _SACIO_DEFAULTS()
SEISMOGRAM_DEFAULTS = _SEISMOGRAM_DEFAULTS()
