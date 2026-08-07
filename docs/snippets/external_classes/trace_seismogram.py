import numpy as np
import pandas as pd
from obspy import Trace, UTCDateTime


class TraceSeismogram:
    def __init__(self, parent: Trace) -> None:
        self._parent = parent

    @property
    def begin_time(self) -> pd.Timestamp:
        return pd.Timestamp(self._parent.stats.starttime.ns, unit="ns", tz="UTC")

    @begin_time.setter
    def begin_time(self, value: pd.Timestamp) -> None:
        self._parent.stats.starttime = UTCDateTime(ns=value.value)

    @property
    def delta(self) -> pd.Timedelta:
        return pd.Timedelta(seconds=self._parent.stats.delta)

    @delta.setter
    def delta(self, value: pd.Timedelta) -> None:
        self._parent.stats.delta = value.total_seconds()

    @property
    def data(self) -> np.ndarray:
        return self._parent.data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        self._parent.data = value

    @property
    def end_time(self) -> pd.Timestamp:
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)
