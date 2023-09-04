import datetime
import numpy as np
from typing import Optional
from .mini import MiniEvent, MiniSeismogram, MiniStation
from pysmo.lib.io import SacIO
from pydantic.dataclasses import dataclass
from pydantic import Field


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

        @property
        def _ref_datetime(self) -> datetime.datetime:
            """
            Returns:
                Reference time date in a SAC file.
            """
            ref_time = datetime.time.fromisoformat(self.parent.kztime)
            ref_date = datetime.date.fromisoformat(self.parent.kzdate)
            return datetime.datetime.combine(ref_date, ref_time)

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
            return self._ref_datetime + datetime.timedelta(seconds=self.parent.b)

        @begin_time.setter
        def begin_time(self, value: datetime.datetime) -> None:
            # Since other sac headers depend on the reference time (e.g . "o"),
            # we don't touch the sac reference time. Instead set the "b"
            # header, which is the difference between event time and
            # reference time in seconds.
            self.parent.b = (value - self._ref_datetime).total_seconds()

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
            # TODO: better error message
            if self.parent.evla is None:
                raise ValueError("Value for event latitude is None.")
            return self.parent.evla

        @latitude.setter
        def latitude(self, value: float) -> None:
            setattr(self.parent, 'evla', value)

        @property
        def longitude(self) -> float:
            # TODO: better error message
            if self.parent.evlo is None:
                raise ValueError("Value for event longitude is None.")
            return self.parent.evlo

        @longitude.setter
        def longitude(self, value: float) -> None:
            setattr(self.parent, 'evlo', value)

        @property
        def depth(self) -> float:
            # TODO: better error message
            if self.parent.evdp is None:
                raise ValueError("Value for event depth is None.")
            return self.parent.evdp * 1000

        @depth.setter
        def depth(self, value: float) -> None:
            setattr(self.parent, 'evdp', value/1000)

        @property
        def time(self) -> datetime.datetime:
            # Event origin time is reference datetime + "o" sac header
            if self.parent.o is None:
                raise ValueError(f"Value for SAC header 'o' is {self.parent.o}. " +
                                 "Unable to set new event origin time.")
            return self._ref_datetime + datetime.timedelta(seconds=self.parent.o)

        @time.setter
        def time(self, value: datetime.datetime) -> None:
            # Since other sac headers depend on the reference time (e.g . "b"),
            # we don't touch the sac reference time. Instead set the "o"
            # header, which is the difference between event time and
            # reference time in seconds.
            self.parent.o = (value - self._ref_datetime).total_seconds()

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
            if self.parent.kstnm is None:
                raise ValueError("Value for SAC header 'kstnm' is undefined." +
                                 "Unable to get station name.")
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
            if self.parent.stla is None:
                raise ValueError("Value for SAC header 'stla' is undefined." +
                                 "Unable to get station latitude.")
            return self.parent.stla

        @latitude.setter
        def latitude(self, value: float) -> None:
            setattr(self.parent, 'stla', value)

        @property
        def longitude(self) -> float:
            if self.parent.stlo is None:
                raise ValueError("Value for SAC header 'stlo' is undefined." +
                                 "Unable to get station longitude.")
            return self.parent.stlo

        @longitude.setter
        def longitude(self, value: float) -> None:
            setattr(self.parent, 'stlo', value)

        @property
        def elevation(self) -> Optional[float]:
            return self.parent.stel

        @elevation.setter
        def elevation(self, value: float) -> None:
            setattr(self.parent, 'stel', value)

    seismogram: SacSeismogram = Field(default=None)
    station: SacStation = Field(default=None)
    event: SacEvent = Field(default=None)

    def __post_init__(self) -> None:
        self.seismogram = self.SacSeismogram(parent=self)
        self.station = self.SacStation(parent=self)
        self.event = self.SacEvent(parent=self)
