__author__ = "Simon Lloyd"

import datetime
import warnings
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from .mini import MiniHypocenter, MiniSeismogram, MiniStation
from pysmo.io import _SacIO


class _SacNested:
    """Base class for nested SAC classes"""

    def __init__(self, parent: _SacIO) -> None:
        self.parent = parent


class _SacSeismogram(_SacNested, MiniSeismogram):
    """Helper class for SAC seismogram attributes.

    The :py:class:`_SacSeismogram` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each new (parent) SAC
    instance to enable pysmo types compatibility.
    """

    @property
    def data(self) -> np.ndarray:
        """The seismogram data."""
        return self.parent.data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        self.parent.data = value

    @property
    def sampling_rate(self) -> float:
        """Seismogram sampling rate."""
        return self.parent.delta

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        self.parent.delta = value

    @property
    def begin_time(self) -> datetime.datetime:
        """Seismogram begin timedate."""
        # Begin time is reference time/date + b
        abs_begin_time = datetime.time.fromisoformat(self.parent.kztime)
        begin_date = datetime.date.fromisoformat(self.parent.kzdate)
        return datetime.datetime.combine(begin_date, abs_begin_time) + \
            datetime.timedelta(seconds=self.parent.b)

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
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
    """Helper class for SAC event attributes.

    The :py:class:`_SacStation` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each new (parent) SAC
    instance to enable pysmo types compatibility.
    """

    @property
    def name(self) -> str:
        """Station name or code."""
        return self.parent.kstnm

    @name.setter
    def name(self, value: str) -> None:
        setattr(self.parent, 'kstnm', value)

    @property
    def network(self) -> str:
        """Network name or code."""
        return self.parent.knetwk

    @network.setter
    def network(self, value: str) -> None:
        setattr(self.parent, 'knetwk', value)

    @property
    def latitude(self) -> float:
        """Station latitude."""
        return self.parent.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        setattr(self.parent, 'stla', value)

    @property
    def longitude(self) -> float:
        """Station longitude."""
        return self.parent.stlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        setattr(self.parent, 'stlo', value)

    @property
    def elevation(self) -> Optional[float]:
        """Station elevation in meters."""
        if self.parent.stel:
            return self.parent.stel
        return None

    @elevation.setter
    def elevation(self, value: float) -> None:
        setattr(self.parent, 'stel', value)


class _SacEvent(_SacNested, MiniHypocenter):
    """Helper class for SAC event attributes.

    The :py:class:`_SacEvent` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each new (parent) SAC
    instance to enable pysmo types compatibility.
    """

    @property
    def latitude(self) -> float:
        """Event Latitude."""
        return self.parent.evla

    @latitude.setter
    def latitude(self, value: float) -> None:
        setattr(self.parent, 'evla', value)

    @property
    def longitude(self) -> float:
        """Event Longitude."""
        return self.parent.evlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        setattr(self.parent, 'evlo', value)

    @property
    def depth(self) -> float:
        """Event depth in meters."""
        return self.parent.evdp * 1000

    @depth.setter
    def depth(self, value: float) -> None:
        setattr(self.parent, 'evdp', value/1000)


@dataclass
class SAC(_SacIO):
    """Class for SAC files.

    The :py:class:`SAC` provides a data structure that mirrors header fields and data as
    presented by the sac fileformat. SAC instances are typically created by reading sac
    file. Data and header fields can be accessed as attributes:

        >>> from pysmo import SAC
        >>> my_sac = SAC.from_file('my_file.sac')
        >>> print(my_sac.delta)
        0.019999999552965164
        >>> print(my_sac.data)
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.])
        >>> my_sac.evla = 23.14
        >>> ...

    Presenting the data in this way is *not* compatible with pysmo types. For example,
    event coordinates are stored in the :py:attr:`evla` and :py:attr:`evlo` attributes,
    which do not match the pysmo :py:class:`Location` type. In order to map these
    incompatible attributes to ones that can be used with pysmo types, we use helper
    classes as a way to access the attributes under different names that *are*
    compatible with pysmo types:

        >>> # Import the Seismogram type to check if the nested class is compatible.
        >>> from pysmo import Seismogram
        >>>
        >>> # First verify that a SAC instance is not a pysmo Seismogram:
        >>> isinstance(my_sac, Seismogram)
        False
        >>> # The my_sac.Seismogram object is, however:
        >>> isinstance(my_sac.Seismogram, Seismogram)
        True

    Note that :py:class:`my_sac.Seismogram` is an instance of the
    :py:class:`_SacSeismogram` helper class. It is created when a new :py:class:`SAC`
    instance is instantiated. For convenience we can access it via a new variable:

        >>> my_seismogram = my_sac.Seismogram
        >>> isinstance(my_seismogram, Seismogram)
        True
        >>> # Verify the helper object is indeed just providing access to the same thing
        >>> # under a different name:
        >>> my_sac.delta is my_seismogram.sampling_rate
        True
    """
    Seismogram: _SacSeismogram = field(init=False)
    """Seismogram is an instance of the :py:class:`_SacSeismogram` helper class."""

    Station: _SacStation = field(init=False)
    """Station is an instance of the :py:class:`_SacStation` helper class."""

    Event: _SacEvent = field(init=False)
    """Event is an instance of the :py:class:`_SacEvent` helper class."""

    def __post_init__(self) -> None:
        self.Seismogram = _SacSeismogram(self)
        self.Station = _SacStation(self)
        self.Event = _SacEvent(self)
