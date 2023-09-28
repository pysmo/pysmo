from pysmo.lib.io import SacIO
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.lib.exceptions import SacHeaderUndefined
from pysmo.lib.decorators import value_not_none
from attrs import define, field
from datetime import datetime, timedelta, time, date
import numpy as np


@define(kw_only=True)
class SAC(SacIO):
    """Class for accessing data in SAC files.

    Tip:
        This class inherits the numerous attributes and methods from the
        [SacIO][pysmo.lib.io.sacio.SacIO] class. This gives access to all
        SAC headers, ability to load from a file, download data, and so on.

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

        Presenting the data in this way is *not* compatible with pysmo types.
        For example, event coordinates are stored in the `evla` and `evlo`
        attributes, which do not match the pysmo [`Location`][pysmo.types.Location]
        type. Renaming or aliasing `evla` to `latitude` and `evlo` to `longitude`
        would solve the problem for the event coordinates, but since the SAC format
        also specifies station coordinates (`stla`, `stlo`) we still would run
        into compatibility issues.

        In order to map these incompatible attributes to ones that can be
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
        >>> my_sac.delta is my_seismogram.delta
        True

        Because the SAC file format defines a large amount of header fields for
        metadata, it needs to allow for many of these to be optional. Since the helper
        classes are more specific (and intended to be used with pysmo types), their
        attributes typically may *not* be [`None`][None]:

        >>> my_sac.evla = None
        >>> # No error: a SAC file doesn't have to contain event information.
        >>> my_sac.event.latitude = None
        TypeError: SacEvent.latitude may not be of None type.
        >>> # Error: the my_sac.event object may not have attributes set to `None`.


    Attributes:
        seismogram: Maps pysmo compatible attributes to the internal SAC attributes.
        station: Maps pysmo compatible attributes to the internal SAC attributes.
        event: Maps pysmo compatible attributes to the internal SAC attributes.
    """

    @define(kw_only=True)
    class _SacNested:
        """Base class for nested SAC classes"""

        _parent: SacIO

        @property
        def _ref_datetime(self) -> datetime:
            """
            Returns:
                Reference time date in a SAC file.
            """
            # The SAC header variable "b" is set to a default value, so
            # it should never b "None" in a SacIO object. We use that
            # to define the reference time in case it is missing in
            # the parent SacIO object.
            # TODO: maybe it needs setting in the SacIO object too?
            if self._parent.kztime is None or self._parent.kzdate is None:
                return SEISMOGRAM_DEFAULTS.begin_time - timedelta(
                    seconds=self._parent.b
                )
            ref_time = time.fromisoformat(self._parent.kztime)
            ref_date = date.fromisoformat(self._parent.kzdate)
            return datetime.combine(ref_date, ref_time)

    @define(kw_only=True)
    class SacSeismogram(_SacNested):
        """Helper class for seismogram attributes.

        The `SacSeismogram` class is used to map SAC attributes in a way that
        matches pysmo types. An instance of this class is created for each new
        (parent) [SAC][pysmo.classes.sac.SAC]instance to enable pysmo types
        compatibility.

        Attributes:
            begin_time: Seismogram begin timedate.
            end_time: Seismogram end time.
            delta: Seismogram sampling interval.
            data: Seismogram data.

        Note:
            Timing operations in a SAC file use a reference time, and all times (begin
            time, event origin time, picks, etc.) are relative to this reference time.
            Here, the `begin_time` is the actual time (in UTC) of the first data point.

            As other time fields in the SAC specification depend on the reference time,
            changing the `begin_time` will adjust only the `b` attribute in the parent
            [`SAC`][pysmo.classes.sac.SAC] instance.
        """

        def __len__(self) -> int:
            return np.size(self.data)

        @property
        def data(self) -> np.ndarray:
            return self._parent.data

        @data.setter
        def data(self, value: np.ndarray) -> None:
            self._parent.data = value

        @property
        def delta(self) -> float:
            return self._parent.delta

        @delta.setter
        def delta(self, value: float) -> None:
            self._parent.delta = value

        @property
        def begin_time(self) -> datetime:
            # "b" header is event origin time relative to the reference time.
            return self._ref_datetime + timedelta(seconds=self._parent.b)

        @begin_time.setter
        @value_not_none
        def begin_time(self, value: datetime) -> None:
            self._parent.b = (value - self._ref_datetime).total_seconds()

        @property
        def end_time(self) -> datetime:
            if len(self) == 0:
                return self.begin_time
            return self.begin_time + timedelta(seconds=self.delta * (len(self) - 1))

    @define(kw_only=True)
    class SacEvent(_SacNested):
        """Helper class for event attributes.

        The `SacEvent` class is used to map SAC attributes in a way that
        matches pysmo types. An instance of this class is created for each
        new (parent) [SAC][pysmo.classes.sac.SAC] instance to enable pysmo
        types compatibility.

        Note:
            Not all SAC files contain event information.

        Attributes:
            latitude: Event Latitude.
            longitude: Event Longitude.
            depth: Event depth in meters.
            time: Event origin time (UTC).
        """

        @property
        def latitude(self) -> float:
            if self._parent.evla is None:
                raise SacHeaderUndefined(header="evla")
            return self._parent.evla

        @latitude.setter
        @value_not_none
        def latitude(self, value: float) -> None:
            setattr(self._parent, "evla", value)

        @property
        def longitude(self) -> float:
            if self._parent.evlo is None:
                raise SacHeaderUndefined(header="evlo")
            return self._parent.evlo

        @longitude.setter
        @value_not_none
        def longitude(self, value: float) -> None:
            setattr(self._parent, "evlo", value)

        @property
        def depth(self) -> float:
            if self._parent.evdp is None:
                raise SacHeaderUndefined(header="evdp")
            return self._parent.evdp * 1000

        @depth.setter
        @value_not_none
        def depth(self, value: float) -> None:
            setattr(self._parent, "evdp", value / 1000)

        @property
        def time(self) -> datetime:
            # "o" header is event origin time relative to the reference time.
            if self._parent.o is None:
                raise SacHeaderUndefined(header="o")
            return self._ref_datetime + timedelta(seconds=self._parent.o)

        @time.setter
        @value_not_none
        def time(self, value: datetime) -> None:
            self._parent.o = (value - self._ref_datetime).total_seconds()

    @define(kw_only=True)
    class SacStation(_SacNested):
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
            if self._parent.kstnm is None:
                raise SacHeaderUndefined(header="kstnm")
            return self._parent.kstnm

        @name.setter
        @value_not_none
        def name(self, value: str) -> None:
            setattr(self._parent, "kstnm", value)

        @property
        def network(self) -> str | None:
            return self._parent.knetwk

        @network.setter
        def network(self, value: str) -> None:
            setattr(self._parent, "knetwk", value)

        @property
        def latitude(self) -> float:
            if self._parent.stla is None:
                raise SacHeaderUndefined(header="stla")
            return self._parent.stla

        @latitude.setter
        @value_not_none
        def latitude(self, value: float) -> None:
            setattr(self._parent, "stla", value)

        @property
        def longitude(self) -> float:
            if self._parent.stlo is None:
                raise SacHeaderUndefined(header="stlo")
            return self._parent.stlo

        @longitude.setter
        @value_not_none
        def longitude(self, value: float) -> None:
            setattr(self._parent, "stlo", value)

        @property
        def elevation(self) -> float | None:
            return self._parent.stel

        @elevation.setter
        def elevation(self, value: float) -> None:
            setattr(self._parent, "stel", value)

    seismogram: SacSeismogram = field(init=False)
    station: SacStation = field(init=False)
    event: SacEvent = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.seismogram = self.SacSeismogram(parent=self)
        self.station = self.SacStation(parent=self)
        self.event = self.SacEvent(parent=self)
