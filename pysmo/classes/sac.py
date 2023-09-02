import datetime
import warnings
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from .mini import MiniEvent, MiniSeismogram, MiniStation
from pysmo.lib.io import SacIO


@dataclass
class SAC(SacIO):
    """Class for SAC files.

    Examples:
        The `SAC` class provides a data structure that mirrors header fields and
        data as presented by the sac fileformat. SAC instances are typically
        created by reading sac file. Data and header fields can be accessed as
        attributes:

        >>> from pysmo import SAC
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> print(my_sac.delta)
        0.019999999552965164
        >>> print(my_sac.data)
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.])
        >>> my_sac.evla = 23.14
        >>> ...

        Presenting the data in this way is *not* compatible with pysmo types.
        For example, event coordinates are stored in the `evla` and `evlo`
        attributes, which do not match the pysmo [`Location`][pysmo.types.Location]
        type. In order to map these incompatible attributes to ones that can be
        used with pysmo types, we use helper classes as a way to access the attributes
        under different names that *are* compatible with pysmo types:

        >>> # Import the Seismogram type to check if the nested class is compatible.
        >>> from pysmo import Seismogram
        >>>
        >>> # First verify that a SAC instance is not a pysmo Seismogram:
        >>> isinstance(my_sac, Seismogram)
        False
        >>> # The my_sac.seismogram object is, however:
        >>> isinstance(my_sac.seismogram, Seismogram)
        True

        Note that `my_sac.seismogram` is an instance of the
        [`SacSeismogram`][pysmo.classes.sac.SAC.SacSeismogram] helper class. It is
        created when a new `SAC` instance is instantiated. For convenience we can
        access it via a new variable:

        >>> my_seismogram = my_sac.seismogram
        >>> isinstance(my_seismogram, Seismogram)
        True
        >>> # Verify the helper object is indeed just providing access to the same thing
        >>> # under a different name:
        >>> my_sac.delta is my_seismogram.sampling_rate
        True

    Tip:
        This class inherits the numerous attributes and methods from the
        [SacIO][pysmo.lib.io.sacio.SacIO] class.

    Attributes:
        seismogram: Maps pysmo compatible attributes to the internal SAC attributes.
        station: Maps pysmo compatible attributes to the internal SAC attributes.
        event: Maps pysmo compatible attributes to the internal SAC attributes.
    """

    class _SacNested:
        """Base class for nested SAC classes"""

        def __init__(self, parent: SacIO) -> None:
            self.parent = parent

    class SacEvent(_SacNested, MiniEvent):
        """Helper class for event attributes.

        The `SacEvent` class is used to map SAC attributes in a way that
        matches pysmo types. An instance of this class is created for each
        new (parent) [SAC][pysmo.classes.sac.SAC] instance to enable pysmo
        types compatibility.

        Attributes:
            latitude: Event Latitude.
            longitude: Event Longitude.
            depth: Event depth in meters.
        """

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
            return self.parent.evdp * 1000

        @depth.setter
        def depth(self, value: float) -> None:
            setattr(self.parent, 'evdp', value/1000)

        @property
        def time(self) -> datetime.datetime:
            # Begin time is reference time/date + "o" sac header
            ref_time = datetime.time.fromisoformat(self.parent.kztime)
            ref_date = datetime.date.fromisoformat(self.parent.kzdate)
            return datetime.datetime.combine(ref_date, ref_time) + \
                datetime.timedelta(seconds=self.parent.o)

        @time.setter
        def time(self, value: datetime.datetime) -> None:
            # Setting the time should change the reference time,
            # so we first subtract o.
            ref_begin_timedate = value - datetime.timedelta(seconds=self.parent.o)

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

    class SacSeismogram(_SacNested, MiniSeismogram):
        """Helper class for seismogram attributes.

        The `SacSeismogram` class is used to map SAC attributes in a way that
        matches pysmo types. An instance of this class is created for each new
        (parent) [SAC][pysmo.classes.sac.SAC]instance to enable pysmo types
        compatibility.

        note:
            Because this class inherits from
            [MiniSeismogram][pysmo.classes.mini.MiniSeismogram], not all
            attributes and methods need to be redifined here (e.g. the
            read-only `end_time`).

        Attributes:
            data: Seismogram data.
            sampling_rate: Seismogram sampling rate.
            begin_time: Seismogram begin timedate.
        """

        @property
        def data(self) -> np.ndarray:
            return self.parent.data

        @data.setter
        def data(self, value: np.ndarray) -> None:
            self.parent.data = value

        @property
        def sampling_rate(self) -> float:
            return self.parent.delta

        @sampling_rate.setter
        def sampling_rate(self, value: float) -> None:
            self.parent.delta = value

        @property
        def begin_time(self) -> datetime.datetime:
            # Begin time is reference time/date + "b" sac header
            ref_time = datetime.time.fromisoformat(self.parent.kztime)
            ref_date = datetime.date.fromisoformat(self.parent.kzdate)
            return datetime.datetime.combine(ref_date, ref_time) + \
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

    class SacStation(_SacNested, MiniStation):
        """Helper class for SAC event attributes.

        The `SacStation` class is used to map SAC attributes in a way that
        matches pysmo types. An instance of this class is created for each
        new (parent) [SAC][pysmo.classes.sac.SAC]instance to enable pysmo
        types compatibility.

        Attributes:
            name: Station name or code.
            network: Network name or code.
            latitude: Station latitude.
            longitude: Station longitude.
            elevation: Station elevation in meters.
        """

        @property
        def name(self) -> str:
            return self.parent.kstnm

        @name.setter
        def name(self, value: str) -> None:
            setattr(self.parent, 'kstnm', value)

        @property
        def network(self) -> Optional[str]:
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

    seismogram: SacSeismogram = field(init=False)
    station: SacStation = field(init=False)
    event: SacEvent = field(init=False)

    def __post_init__(self) -> None:
        super()._set_defaults()
        self.seismogram = self.SacSeismogram(self)
        self.station = self.SacStation(self)
        self.event = self.SacEvent(self)
