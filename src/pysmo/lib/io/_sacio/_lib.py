from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.tools.utils import to_seconds
from dataclasses import dataclass


@dataclass(frozen=True)
class _SACIO_DEFAULTS:
    """SacIO defaults."""

    b: float = 0
    delta: float = to_seconds(SEISMOGRAM_DEFAULTS.delta.value)
    nvhdr: int = 7
    iftype: str = "time"
    idep: str = "unkn"
    iztype: str = "unkn"
    ievtyp: str = "unkn"
    leven: bool = True
    iris_base_url: str = "https://service.iris.edu/irisws/timeseries/1/query"
    iris_timeout_seconds: int = 10
    iris_request_retries: int = 3
    iris_retry_delay_seconds: int = 20


SACIO_DEFAULTS = _SACIO_DEFAULTS()
