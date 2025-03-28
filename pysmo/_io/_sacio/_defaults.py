from dataclasses import dataclass


@dataclass(frozen=True)
class _SACIO_DEFAULTS:
    """SacIO defaults."""

    b: float = 0
    delta: float = 1
    nvhdr: int = 7
    iftype: str = "time"
    idep: str = "unkn"
    iztype: str = "unkn"
    ievtyp: str = "unkn"
    leven: bool = True


SACIO_DEFAULTS = _SACIO_DEFAULTS()
