from typing import Literal, get_args, overload, Self
from pysmo._io import SacIO, SacHeaderUndefined
from pysmo._lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo._lib.decorators import value_not_none
from attrs import define, field
from datetime import datetime, timedelta, time, date, timezone
import numpy as np
import numpy.typing as npt

__all__ = [
    "SAC",
    "SacSeismogram",
    "SacEvent",
    "SacStation",
    "SacTimestamps",
]

TSacTimeHeaders = Literal[
    "b", "e", "o", "a", "f", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"
]
SAC_TIME_HEADERS: tuple[TSacTimeHeaders, ...] = get_args(TSacTimeHeaders)


@define(kw_only=True)
class _SacNested:
    """Base class for nested SAC classes."""

    _parent: SacIO = field(repr=False)
    """_parent (SacIO): Parent SacIO instance."""

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
            return SEISMOGRAM_DEFAULTS.begin_time - timedelta(seconds=self._parent.b)
        ref_time = time.fromisoformat(self._parent.kztime)
        ref_date = date.fromisoformat(self._parent.kzdate)
        return datetime.combine(date=ref_date, time=ref_time, tzinfo=timezone.utc)

    def _get_datetime_from_sac(
        self, sac_time_header: TSacTimeHeaders
    ) -> datetime | None:
        """Convert SAC times to datetime."""
        seconds = getattr(self._parent, sac_time_header)
        if seconds is None:
            return None
        return self._ref_datetime + timedelta(seconds=seconds)

    def _set_sac_from_datetime(
        self, sac_time_header: TSacTimeHeaders, value: datetime
    ) -> None:
        """Set SAC times using datetimes."""
        seconds = (value - self._ref_datetime).total_seconds()
        setattr(self._parent, sac_time_header, seconds)


@define(kw_only=True)
class SacSeismogram(_SacNested):
    """Helper class for SAC seismogram attributes.

    The `SacSeismogram` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each new
    (parent) [`SAC`][pysmo.classes.SAC] instance to enable pysmo types
    compatibility.

    Examples:
        Checking if a SacSeismogram matches the pysmo
        [`Seismogram`][pysmo.Seismogram] type:

        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> isinstance(my_sac.seismogram, Seismogram)
        True
        >>>

        Timing operations in a SAC file use a reference time, and all times
        (begin time, event origin time, picks, etc.) are relative to this
        reference time. In pysmo only absolute times are used. The example
        below shows the `begin_time` is the absolute time (in UTC) of the first
        data point:

        >>> from pysmo import SAC
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> my_sac.seismogram.begin_time
        datetime.datetime(2005, 3, 1, 7, 23, 2, 160000, tzinfo=datetime.timezone.utc)
        >>>
    """

    def __len__(self) -> int:
        return np.size(self.data)

    @property
    def data(self) -> npt.NDArray:
        """Seismogram data."""

        return self._parent.data

    @data.setter
    def data(self, value: npt.NDArray) -> None:
        self._parent.data = value

    @property
    def delta(self) -> timedelta:
        """Sampling interval."""
        return timedelta(seconds=self._parent.delta)

    @delta.setter
    def delta(self, value: timedelta) -> None:
        self._parent.delta = value.total_seconds()

    @property
    def begin_time(self) -> datetime:
        """Seismogram begin time."""
        value = self._get_datetime_from_sac("b")
        if value is None:
            raise SacHeaderUndefined(header="b")
        return value

    @begin_time.setter
    @value_not_none
    def begin_time(self, value: datetime) -> None:
        self._set_sac_from_datetime("b", value)

    @property
    def end_time(self) -> datetime:
        """Seismogram end time."""
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self) - 1)


@define(kw_only=True)
class SacStation(_SacNested):
    """Helper class for SAC station attributes.

    The `SacStation` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each
    new (parent) [`SAC`][pysmo.classes.SAC]instance to enable pysmo
    types compatibility.

    Examples:
        Checking if a SacStation matches the pysmo
        [`Station`][pysmo.Station] type:

        >>> from pysmo import SAC, Station
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> isinstance(my_sac.station, Station)
        True
        >>>
    """

    @property
    def name(self) -> str:
        """Station name or code."""

        if self._parent.kstnm is None:
            raise SacHeaderUndefined(header="kstnm")
        return self._parent.kstnm

    @name.setter
    @value_not_none
    def name(self, value: str) -> None:
        setattr(self._parent, "kstnm", value)

    @property
    def network(self) -> str | None:
        """Network name or code."""
        return self._parent.knetwk

    @network.setter
    def network(self, value: str) -> None:
        setattr(self._parent, "knetwk", value)

    @property
    def latitude(self) -> float:
        """Station latitude."""
        if self._parent.stla is None:
            raise SacHeaderUndefined(header="stla")
        return self._parent.stla

    @latitude.setter
    @value_not_none
    def latitude(self, value: float) -> None:
        setattr(self._parent, "stla", value)

    @property
    def longitude(self) -> float:
        """Station longitude."""
        if self._parent.stlo is None:
            raise SacHeaderUndefined(header="stlo")
        return self._parent.stlo

    @longitude.setter
    @value_not_none
    def longitude(self, value: float) -> None:
        setattr(self._parent, "stlo", value)

    @property
    def elevation(self) -> float | None:
        """Station elevation in meters."""
        return self._parent.stel

    @elevation.setter
    def elevation(self, value: float) -> None:
        setattr(self._parent, "stel", value)


@define(kw_only=True)
class SacEvent(_SacNested):
    """Helper class for SAC event attributes.

    The `SacEvent` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each
    new (parent) [`SAC`][pysmo.classes.SAC] instance to enable pysmo
    types compatibility.

    Examples:
        Checking if a SacEvent matches the pysmo
        [`Event`][pysmo.Event] type:

        >>> from pysmo import SAC, Event
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> isinstance(my_sac.event, Event)
        True
        >>>

    Note:
        Not all SAC files contain event information.
    """

    @property
    def latitude(self) -> float:
        """Event Latitude."""

        if self._parent.evla is None:
            raise SacHeaderUndefined(header="evla")
        return self._parent.evla

    @latitude.setter
    @value_not_none
    def latitude(self, value: float) -> None:
        setattr(self._parent, "evla", value)

    @property
    def longitude(self) -> float:
        """Event Longitude."""

        if self._parent.evlo is None:
            raise SacHeaderUndefined(header="evlo")
        return self._parent.evlo

    @longitude.setter
    @value_not_none
    def longitude(self, value: float) -> None:
        setattr(self._parent, "evlo", value)

    @property
    def depth(self) -> float:
        """Event depth in meters."""
        if self._parent.evdp is None:
            raise SacHeaderUndefined(header="evdp")
        return self._parent.evdp * 1000

    @depth.setter
    @value_not_none
    def depth(self, value: float) -> None:
        setattr(self._parent, "evdp", value / 1000)

    @property
    def time(self) -> datetime:
        """Event origin time (UTC)."""
        event_time = self._get_datetime_from_sac("o")
        if event_time is None:
            raise SacHeaderUndefined(header="o")
        return event_time

    @time.setter
    @value_not_none
    def time(self, value: datetime) -> None:
        self._set_sac_from_datetime("o", value)


class SacTimeConverter:
    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly

    def __set_name__(self, _: _SacNested, name: TSacTimeHeaders) -> None:
        self._name: TSacTimeHeaders = name

    @overload
    def __get__(self, instance: None, owner: None) -> Self: ...

    @overload
    def __get__(self, instance: _SacNested, owner: type[object]) -> datetime | None: ...

    def __get__(
        self, instance: _SacNested | None, owner: type[object] | None = None
    ) -> Self | datetime | None:
        if instance is None:
            return self
        return instance._get_datetime_from_sac(self._name)

    def __set__(self, obj: _SacNested, value: datetime) -> None:
        if self.readonly:
            raise AttributeError(f"SAC header '{self._name}' is read only.")
        obj._set_sac_from_datetime(self._name, value)


class SacTimestamps(_SacNested):
    """Helper class to access times stored in SAC headers as datetime objects.

    The `SacTimestamps` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each
    new (parent) [`SAC`][pysmo.classes.SAC] instance to enable pysmo
    types compatibility.


    Examples:
        Relative seismogram begin time as a float vs absolute begin time
        as a [datetime][datetime] object.

        ```python
        >>> from pysmo import SAC
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> # SAC header "B" as stored in a SAC file
        >>> my_sac.b
        -63.34
        >>> # the output above is the number of seconds relative
        >>> # to the reference time and date:
        >>> my_sac.kzdate , my_sac.kztime
        ('2005-03-01', '07:24:05.500')
        >>> # Accessing the same SAC header via a `SacTimestamps` object
        >>> # yields a corresponding datetime object with the absolute time:
        >>> my_sac.timestamps.b
        datetime.datetime(2005, 3, 1, 7, 23, 2, 160000, tzinfo=datetime.timezone.utc)
        ```

        Changing timestamp values:

        ```python
        >>> from datetime import timedelta
        >>> from pysmo.classes import SAC
        >>> my_sac = SAC.from_file("testfile.sac")
        >>> # Original value of the "B" SAC header:
        >>> my_sac.b
        -63.34
        >>> # Add 30 seconds to the absolute time:
        >>> my_sac.timestamps.b += timedelta(seconds=30)
        >>> # The relative time also changes by the same amount:
        >>> my_sac.b
        -33.34
        ```
    """

    b: SacTimeConverter = SacTimeConverter()
    """Beginning time of the independent variable."""

    e: SacTimeConverter = SacTimeConverter(readonly=True)
    """Ending time of the independent variable (read-only)."""

    o: SacTimeConverter = SacTimeConverter()
    """Event origin time."""

    a: SacTimeConverter = SacTimeConverter()
    """First arrival time."""

    f: SacTimeConverter = SacTimeConverter()
    """Fini or end of event time."""

    t0: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 0."""

    t1: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 1."""

    t2: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 2."""

    t3: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 3."""

    t4: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 4."""

    t5: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 5."""

    t6: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 6."""

    t7: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 7."""

    t8: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 8."""

    t9: SacTimeConverter = SacTimeConverter()
    """User defined time pick or marker 9."""


@define(kw_only=True)
class SAC(SacIO):
    """Access and modify data stored in SAC files.

    The [`SAC`][pysmo.classes.SAC] class inherits all attributes and methods
    of the [`SacIO`][pysmo._io.SacIO] class, and extends it with attributes
    that allow using pysmo types. The extra attributes are themselves instances
    of "helper" classes that cannot be instantiated directly.

    Examples:
        SAC instances are typically created by reading a SAC file. Users
        familiar with the SAC file format can access header and data using
        the names they are used to:

        ```python
        >>> from pysmo.classes import SAC
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> my_sac.delta
        0.019999999552965164
        >>> my_sac.data
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.])
        >>> my_sac.evla
        23.14
        >>>
        ```

        Presenting the data in the above way is *not* compatible with pysmo
        types. For example, event coordinates are stored in the
        [`evla`][pysmo._io.SacIO.evla] and [`evlo`][pysmo._io.SacIO.evlo]
        attributes, which do not match the pysmo [`Location`][pysmo.Location]
        type. Renaming or aliasing `evla` to `latitude` and `evlo` to
        `longitude` would solve the problem for the event coordinates, but
        since the SAC format also specifies station coordinates
        ([`stla`][pysmo._io.SacIO.stla], [`stlo`][pysmo._io.SacIO.stlo]) we
        still run into compatibility issues.

        In order to map these incompatible attributes to ones that can be
        used with pysmo types, we use helper classes as a way to access the
        attributes under different names that *are* compatible with pysmo
        types:

        ```python
        >>> # Import the Seismogram type to check if the nested class is compatible.
        >>> from pysmo import Seismogram
        >>>
        >>> # First verify that a SAC instance is not a pysmo Seismogram:
        >>> isinstance(my_sac, Seismogram)
        False
        >>> # The my_sac.seismogram object is, however:
        >>> isinstance(my_sac.seismogram, Seismogram)
        True
        >>>
        ```

        Because the SAC file format defines a large amount of header fields for
        metadata, it needs to allow for many of these to be optional. Since the
        helper classes are more specific (and intended to be used with pysmo
        types), their attributes typically may *not* be [`None`][None]:

        ```python
        >>> my_sac.evla = None
        >>> # No error: a SAC file doesn't have to contain event information.
        >>> my_sac.event.latitude = None
        TypeError: SacEvent.latitude may not be of None type.
        >>> # Error: the my_sac.event object may not have attributes set to `None`.
        >>>
        ```

    Tip:
        The [`SAC`][pysmo.classes.SAC] class directly inherits from the
        [`SacIO`][pysmo._io.SacIO] class. This gives access to all
        SAC headers, ability to load from a file, download data, and so on.
        Using [`SAC`][pysmo.classes.SAC] is therefore almost always
        preferred over using [`SacIO`][pysmo._io.SacIO].
    """

    seismogram: SacSeismogram = field(init=False)
    """Access data stored in the SAC object compatible with the [`Seismogram`][pysmo.Seismogram] type."""

    station: SacStation = field(init=False)
    """Access data stored in the SAC object compatible with the [`Station`][pysmo.Station] type."""

    event: SacEvent = field(init=False)
    """Access data stored in the SAC object compatible with the [`Event`][pysmo.Event] type."""

    timestamps: SacTimestamps = field(init=False)
    """Maps a SAC times such as B, E, O, T0-T9 to datetime objects."""

    def __attrs_post_init__(self) -> None:
        self.seismogram = SacSeismogram(parent=self)
        self.station = SacStation(parent=self)
        self.event = SacEvent(parent=self)
        self.timestamps = SacTimestamps(parent=self)
