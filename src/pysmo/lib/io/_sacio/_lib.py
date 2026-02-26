from pysmo.lib.defaults import SeismogramDefaults
from dataclasses import dataclass
from typing import Self

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
    iris_base_url: str = "https://service.iris.edu/irisws/timeseries/1/query"
    iris_timeout_seconds: int = 10
    iris_request_retries: int = 3
    iris_retry_delay_seconds: int = 20
