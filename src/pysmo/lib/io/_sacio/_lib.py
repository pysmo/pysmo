from dataclasses import dataclass
from typing import Self

from pysmo.lib.defaults import SeismogramDefaults

__all__ = ["SacIODefaults"]


@dataclass(init=False)
class SacIODefaults:
    """SacIO defaults."""

    def __new__(cls) -> Self:
        raise RuntimeError(
            "SacIODefaults is not meant to be instantiated. Use SacIODefaults.<attribute> instead."
        )

    b: float = 0
    delta: float = SeismogramDefaults.delta.total_seconds()
    nvhdr: int = 7
    iftype: str = "time"
    idep: str = "unkn"
    iztype: str = "unkn"
    ievtyp: str = "unkn"
    leven: bool = True
    earthscope_base_url: str = (
        "https://service.earthscope.org/irisws/timeseries/1/query"
    )
    earthscope_timeout_seconds: int = 10
    earthscope_request_retries: int = 3
    earthscope_retry_delay_seconds: int = 20
