__author__ = "Simon Lloyd"

import datetime
import warnings
import numpy as np
from typing import Any, Optional
from .mini import MiniHypocenter, MiniSeismogram, MiniStation
from pysmo.io import _SacIO


class _SacNested:
    """Base class for nested SAC classes"""

    def __init__(self, parent: _SacIO) -> None:
        self.parent = parent


class _SacSeismogram(_SacNested, MiniSeismogram):
    """Class for SAC seismogram attributes"""

    @property
    def data(self) -> np.ndarray:
        """Returns seismogram data"""
        return self.parent.data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        self.parent.data = value

    @property
    def sampling_rate(self) -> float:
        """Returns the sampling rate."""
        return self.parent.delta

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        """Sets the sampling rate."""
        self.parent.delta = value

    @property
    def begin_time(self) -> datetime.datetime:
        """Returns the begin timedate."""
        # Begin time is reference time/date + b
        abs_begin_time = datetime.time.fromisoformat(self.parent.kztime)
        begin_date = datetime.date.fromisoformat(self.parent.kzdate)
        return datetime.datetime.combine(begin_date, abs_begin_time) + \
            datetime.timedelta(seconds=self.parent.b)

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        """Sets the begin timedate."""
        # Setting the time should change the reference time,
        # so we first subtract b.
        ref_begin_timedate = value - datetime.timedelta(seconds=self.parent.b)

        # datetime uses microsecond precision, while sac only does milliseconds
        # We go ahead, but we round the values and raise a warning
        if not (ref_begin_timedate.microsecond / 1000).is_integer():
            warnings.warn("SAC file format only has millisecond precision. \
                            Rounding microseconds to milliseconds.", RuntimeWarning)
            ref_begin_timedate += datetime.timedelta(microseconds=500)

        # Now extract individual time components
        self.parent.nzyear = ref_begin_timedate.year
        self.parent.nzjday = ref_begin_timedate.timetuple().tm_yday
        self.parent.nzhour = ref_begin_timedate.hour
        self.parent.nzmin = ref_begin_timedate.minute
        self.parent.nzsec = ref_begin_timedate.second
        self.parent.nzmsec = int(ref_begin_timedate.microsecond / 1000)


class _SacStation(_SacNested, MiniStation):
    """Class for SAC station attributes."""

    @property
    def name(self) -> str:
        return self.parent.kstnm

    @name.setter
    def name(self, value: str) -> None:
        setattr(self.parent, 'kstnm', value)

    @property
    def network(self) -> str:
        return self.parent.knetwk

    @network.setter
    def network(self, value: str) -> None:
        setattr(self.parent, 'knetwk', value)

    @property
    def latitude(self) -> float:
        return self.parent.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        setattr(self.parent, 'stla', value)

    @property
    def longitude(self) -> float:
        return self.parent.stlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        setattr(self.parent, 'stlo', value)

    @property
    def elevation(self) -> Optional[float]:
        if self.parent.stel:
            return self.parent.stel
        return None

    @elevation.setter
    def elevation(self, value: float) -> None:
        setattr(self.parent, 'stel', value)


class _SacEvent(_SacNested, MiniHypocenter):
    """Class for SAC Event attributes."""

    @property
    def latitude(self) -> float:
        return self.parent.evla

    @latitude.setter
    def latitude(self, value: float) -> None:
        setattr(self.parent, 'evla', value)

    @property
    def longitude(self) -> float:
        return self.parent.evlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        setattr(self.parent, 'evlo', value)

    @property
    def depth(self) -> float:
        """Gets the event depth in meters."""
        return self.parent.evdp * 1000

    @depth.setter
    def depth(self, value: float) -> None:
        """Sets the event depth."""
        setattr(self.parent, 'evdp', value/1000)


class SAC(_SacIO):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.Seismogram = _SacSeismogram(self)
        self.Station = _SacStation(self)
        self.Event = _SacEvent(self)
