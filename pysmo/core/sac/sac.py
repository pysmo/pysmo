__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"

import datetime
import warnings
from typing import Any, Optional
from pysmo.core.sac.sacio import _SacIO


class _SacStation(_SacIO):
    """Class for SAC station attributes."""
    @property
    def name(self) -> str:
        return self.kstnm

    @name.setter
    def name(self, value: str) -> None:
        setattr(self, 'kstnm', value)

    @property
    def station_latitude(self) -> float:
        return self.stla

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        setattr(self, 'stla', value)

    @property
    def station_longitude(self) -> float:
        return self.stlo

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        setattr(self, 'stlo', value)

    @property
    def station_elevation(self) -> Optional[float]:
        if self.stel:
            return self.stel
        return None

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        setattr(self, 'stel', value)


class _SacEvent(_SacIO):
    """Class for SAC event attributes."""
    @property
    def event_latitude(self) -> float:
        return self.evla

    @event_latitude.setter
    def event_latitude(self, value: float) -> None:
        setattr(self, 'evla', value)

    @property
    def event_longitude(self) -> float:
        return self.evlo

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        setattr(self, 'evlo', value)

    @property
    def event_depth(self) -> Optional[float]:
        """Gets the event depth in meters."""
        if self.evdp:
            return self.evdp * 1000
        return None

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        setattr(self, 'evdp', value/1000)

    @property
    def event_time(self) -> datetime.datetime:
        """Returns the event timedate."""
        time = datetime.time.fromisoformat(self.kztime)
        date = datetime.date.fromisoformat(self.kzdate)
        return datetime.datetime.combine(date, time)

    @event_time.setter
    def event_time(self, value: datetime.datetime) -> None:
        """Sets the event timedate."""
        # datetime uses microsecond precision, while sac only does milliseconds
        # We go ahead, but we round the values and raise a warning
        if not (value.microsecond / 1000).is_integer():
            warnings.warn("SAC file format only has millisecond precision. \
                          Rounding microseconds to milliseconds.", RuntimeWarning)
            value += datetime.timedelta(microseconds=500)
        self.nzyear = value.year
        self.nzjday = value.timetuple().tm_yday
        self.nzhour = value.hour
        self.nzmin = value.minute
        self.nzsec = value.second
        self.nzmsec = int(value.microsecond / 1000)


class _SacSeismogram(_SacIO):
    """Class for SAC seismogram attributes"""
    def __len__(self) -> int:
        return len(self.data)

    @property
    def sampling_rate(self) -> float:
        """Returns the sampling rate."""
        return self.delta

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        """Sets the sampling rate."""
        self.delta = value

    @property
    def begin_time(self) -> datetime.datetime:
        """Returns the begin timedate."""
        # Begin time is reference time/date + b
        abs_begin_time = datetime.time.fromisoformat(self.kztime)
        begin_date = datetime.date.fromisoformat(self.kzdate)
        return datetime.datetime.combine(begin_date, abs_begin_time) + datetime.timedelta(seconds=self.b)

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        """Sets the begin timedate."""
        # setting the time should change the reference time, so we first subtract b
        ref_begin_timedate = value - datetime.timedelta(seconds=self.b)

        # datetime uses microsecond precision, while sac only does milliseconds
        # We go ahead, but we round the values and raise a warning
        if not (ref_begin_timedate.microsecond / 1000).is_integer():
            warnings.warn("SAC file format only has millisecond precision. \
                          Rounding microseconds to milliseconds.", RuntimeWarning)
            ref_begin_timedate += datetime.timedelta(microseconds=500)

        # Now extract individual time components
        self.nzyear = ref_begin_timedate.year
        self.nzjday = ref_begin_timedate.timetuple().tm_yday
        self.nzhour = ref_begin_timedate.hour
        self.nzmin = ref_begin_timedate.minute
        self.nzsec = ref_begin_timedate.second
        self.nzmsec = int(ref_begin_timedate.microsecond / 1000)

    @property
    def end_time(self) -> datetime.datetime:
        """Returns the end time."""
        return self.begin_time + datetime.timedelta(seconds=self.delta*(len(self)-1))

    @property
    def id(self) -> str:
        """Returns the seismogram ID"""
        return f"{self.knetwk}.{self.kstnm}.{self.khole}.{self.kcmpnm}"


class SAC(_SacSeismogram, _SacStation, _SacEvent):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
