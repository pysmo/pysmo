from dataclasses import dataclass
from typing import Self

from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.http import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
)

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
    # Shared with pysmo.tools.web._EarthScopeDefaults via pysmo.lib.http's
    # module-level constants (the lowest-level module both already depend
    # on), not duplicated literals: lib.io sits below tools.web in the
    # dependency layering, so it cannot import from tools.web directly, but
    # both can import from lib.http.
    earthscope_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    earthscope_request_retries: int = DEFAULT_REQUEST_RETRIES
    earthscope_retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS
