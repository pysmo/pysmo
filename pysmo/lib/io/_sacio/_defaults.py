from dataclasses import dataclass
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS


@dataclass(frozen=True)
class _SACIO_DEFAULTS:
    """SacIO defaults."""

    b: float = 0
    delta: float = SEISMOGRAM_DEFAULTS.delta.value.total_seconds()
    nvhdr: int = 7
    iftype: str = "time"
    idep: str = "unkn"
    iztype: str = "unkn"
    ievtyp: str = "unkn"
    leven: bool = True


SACIO_DEFAULTS = _SACIO_DEFAULTS()
