from __future__ import annotations
from pysmo._types._seismogram import SeismogramEndtimeMixin
from pysmo.lib.io import SacIO
from pysmo.lib.io._sacio import (
    SAC_REQUIRED_TIME_HEADERS,
    SAC_OPTIONAL_TIME_HEADERS,
)
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.lib.decorators import value_not_none
from pandas import Timestamp, Timedelta
from typing import overload, Self, TYPE_CHECKING
from attrs import define, field
import warnings
import numpy as np

__all__ = [
    "SAC",
    "SacSeismogram",
    "SacEvent",
    "SacStation",
    "SacTimestamps",
]


@define(kw_only=True)
class _SacNested:
    """Base class for nested SAC classes."""

    _parent: SacIO = field(repr=False)
    """_parent (SacIO): Parent SacIO instance."""

    @property
    def _ref_datetime(self) -> Timestamp:
        """
        Returns:
            Reference time date in a SAC file.

        Note:
            If the SAC instance has no reference time this function assumes
            that it is equal to `SEISMOGRAM_DEFAULTS.begin_time`.
        """

        if self._parent.ref_datetime is not None:
            return Timestamp(self._parent.ref_datetime)

        warnings.warn(
            f"SAC object has no reference time (kzdate/kztime), assuming {SEISMOGRAM_DEFAULTS.begin_time.value.isoformat()}",
            RuntimeWarning,
        )
        return SEISMOGRAM_DEFAULTS.begin_time.value

    @overload
    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS
    ) -> Timestamp: ...

    @overload
    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_OPTIONAL_TIME_HEADERS
    ) -> Timestamp | None: ...

    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS | SAC_OPTIONAL_TIME_HEADERS
    ) -> Timestamp | None:
        """Convert SAC times to Timestamp."""

        seconds = getattr(self._parent, sac_time_header)

        if seconds is None:
            return None

        return self._ref_datetime + Timedelta(seconds=seconds)

    @overload
    def _set_sac_from_timestamp(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS, value: Timestamp
    ) -> None: ...

    @overload
    def _set_sac_from_timestamp(
        self, sac_time_header: SAC_OPTIONAL_TIME_HEADERS, value: Timestamp | None
    ) -> None: ...

    def _set_sac_from_timestamp(
        self,
        sac_time_header: SAC_REQUIRED_TIME_HEADERS | SAC_OPTIONAL_TIME_HEADERS,
        value: Timestamp | None,
    ) -> None:
        """Set SAC times using Timestamp."""

        if value is None:
            if isinstance(sac_time_header, SAC_REQUIRED_TIME_HEADERS):
                raise TypeError(f"SAC time header '{sac_time_header}' may not be None.")
            setattr(self._parent, sac_time_header, None)
            return
        seconds = (value - self._ref_datetime).total_seconds()
        setattr(self._parent, sac_time_header, seconds)


@define(kw_only=True)
class SacSeismogram(_SacNested, SeismogramEndtimeMixin):
    """Helper class for SAC seismogram attributes.

    The `SacSeismogram` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each new
    (parent) [`SAC`][pysmo.classes.SAC] instance to enable pysmo types
    compatibility.

    Examples:
        Checking if a SacSeismogram matches the pysmo
        [`Seismogram`][pysmo.Seismogram] type:

        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC
        >>> sac = SAC.from_file("example.sac")
        >>> isinstance(sac.seismogram, Seismogram)
        True
        >>>
        ```

        Timing operations in a SAC file use a reference time, and all times
        (begin time, event origin time, picks, etc.) are relative to this
        reference time. In pysmo only absolute times are used. The example
        below shows the `begin_time` is the absolute time (in UTC) of the first
        data point:

        ```python
        >>> sac.seismogram.begin_time
        Timestamp('2005-03-01 07:23:02.159999848+0000', tz='UTC')
        >>>
        ```
    """

    if TYPE_CHECKING:
        data: np.ndarray = field(init=False)
        delta: Timedelta = field(init=False)
        begin_time: Timestamp = field(init=False)

    else:

        @property
        def data(self) -> np.ndarray:
            """Seismogram data."""

            return self._parent.data

        @data.setter
        def data(self, value: np.ndarray) -> None:
            self._parent.data = value

        @property
        def delta(self) -> Timedelta:
            """Sampling interval."""
            return Timedelta(seconds=self._parent.delta)

        @delta.setter
        def delta(self, value: Timedelta) -> None:
            self._parent.delta = value.total_seconds()

        @property
        def begin_time(self) -> Timestamp:
            """Seismogram begin time."""

            return self._get_timestamp_from_sac(SAC_REQUIRED_TIME_HEADERS.b)

        @begin_time.setter
        @value_not_none
        def begin_time(self, value: Timestamp) -> None:
            self._set_sac_from_timestamp(SAC_REQUIRED_TIME_HEADERS.b, value)


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

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo import Station
        >>> sac = SAC.from_file("example.sac")
        >>> isinstance(sac.station, Station)
        True
        >>>
        ```
    """

    @property
    def name(self) -> str:
        """Station name or code."""

        if self._parent.kstnm is None:
            raise TypeError("SAC object station name 'kstnm' is None.")
        return self._parent.kstnm

    @name.setter
    @value_not_none
    def name(self, value: str) -> None:
        setattr(self._parent, "kstnm", value)

    @property
    def network(self) -> str:
        """Network name or code."""

        if self._parent.knetwk is None:
            raise TypeError("SAC object network name 'knetwk' is None.")

        return self._parent.knetwk

    @network.setter
    @value_not_none
    def network(self, value: str) -> None:
        setattr(self._parent, "knetwk", value)

    @property
    def location(self) -> str:
        """Location code."""

        if self._parent.khole is None:
            raise TypeError("SAC object location code 'khole' is None.")
        return self._parent.khole

    @location.setter
    @value_not_none
    def location(self, value: str) -> None:
        setattr(self._parent, "khole", value)

    @property
    def channel(self) -> str:
        """Channel code."""

        if self._parent.kcmpnm is None:
            raise TypeError("SAC object channel code 'kcmpnm' is None.")
        return self._parent.kcmpnm

    @channel.setter
    @value_not_none
    def channel(self, value: str) -> None:
        setattr(self._parent, "kcmpnm", value)

    @property
    def latitude(self) -> float:
        """Station latitude."""

        if self._parent.stla is None:
            raise TypeError("SAC object station latitude 'stla' is None.")
        return self._parent.stla

    @latitude.setter
    @value_not_none
    def latitude(self, value: float) -> None:
        setattr(self._parent, "stla", value)

    @property
    def longitude(self) -> float:
        """Station longitude."""

        if self._parent.stlo is None:
            raise TypeError("SAC object station longitude 'stlo' is None.")
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
    def elevation(self, value: float | None) -> None:
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

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo import Event
        >>> sac = SAC.from_file("example.sac")
        >>> isinstance(sac.event, Event)
        True
        >>>
        ```

    Note:
        Not all SAC files contain event information.
    """

    @property
    def latitude(self) -> float:
        """Event Latitude."""

        if self._parent.evla is None:
            raise TypeError("SAC object event latitude 'evla' is None.")
        return self._parent.evla

    @latitude.setter
    @value_not_none
    def latitude(self, value: float) -> None:
        setattr(self._parent, "evla", value)

    @property
    def longitude(self) -> float:
        """Event Longitude."""

        if self._parent.evlo is None:
            raise TypeError("SAC object event longitude 'evlo' is None.")
        return self._parent.evlo

    @longitude.setter
    @value_not_none
    def longitude(self, value: float) -> None:
        setattr(self._parent, "evlo", value)

    @property
    def depth(self) -> float:
        """Event depth in meters."""

        if self._parent.evdp is None:
            raise TypeError("Sac object event depth 'evdp' is None.")
        return self._parent.evdp * 1000

    @depth.setter
    @value_not_none
    def depth(self, value: float) -> None:
        setattr(self._parent, "evdp", value / 1000)

    @property
    def time(self) -> Timestamp:
        """Event origin time (UTC).

        Important:
            This property uses the [`SacIO.o`][pysmo.lib.io.SacIO.o] time
            header. If [`SacIO.iztype`][pysmo.lib.io.SacIO.iztype] is set to
            `"o"`, then this is also the "Reference time equivalance" and
            [`SacIO.o`][pysmo.lib.io.SacIO.o] cannot be changed (it is always
            0). Changing the [`time`][pysmo.classes.SacEvent.time] directly
            is not possible if this is is the case.
        """

        event_time = self._get_timestamp_from_sac(SAC_OPTIONAL_TIME_HEADERS.o)
        if event_time is None:
            raise TypeError("SAC object event time 'o' is None.")
        return event_time

    @time.setter
    @value_not_none
    def time(self, value: Timestamp) -> None:
        self._set_sac_from_timestamp(SAC_OPTIONAL_TIME_HEADERS.o, value)


class RequiredSacTimestamp:
    """Descriptor for SAC headers that MUST exist and cannot be None.

    Args:
        readonly (bool): If True, prevents modification of the header.
    """

    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly

    def __set_name__(self, owner: type["_SacNested"], name: str) -> None:
        # Validates that this attribute name is a strictly required header
        self._name = SAC_REQUIRED_TIME_HEADERS(name)

    @overload
    def __get__(self, instance: None, owner: type["_SacNested"]) -> Self: ...

    @overload
    def __get__(
        self, instance: "_SacNested", owner: type["_SacNested"]
    ) -> Timestamp: ...

    def __get__(
        self, instance: "_SacNested" | None, owner: type["_SacNested"] | None = None
    ) -> Self | Timestamp:
        if instance is None:
            return self

        seconds = getattr(instance._parent, self._name)

        if seconds is None:
            raise ValueError(
                f"Required SAC header '{self._name}' is missing or None "
                f"on {type(instance).__name__}."
            )

        return instance._ref_datetime + Timedelta(seconds=seconds)

    def __set__(self, obj: "_SacNested", value: Timestamp) -> None:
        if self.readonly:
            raise AttributeError(f"SAC header '{self._name}' is read-only.")
        if value is None:
            raise TypeError(f"SAC time header '{self._name}' may not be None.")

        seconds = (value - obj._ref_datetime).total_seconds()
        setattr(obj._parent, self._name, seconds)


class OptionalSacTimestamp:
    """Descriptor for SAC headers that might be missing or set to None.

    Args:
        readonly (bool): If True, prevents modification of the header.
    """

    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly

    def __set_name__(self, owner: type["_SacNested"], name: str) -> None:
        # Validates that this attribute name is an optional header
        self._name = SAC_OPTIONAL_TIME_HEADERS(name)

    @overload
    def __get__(self, instance: None, owner: type["_SacNested"]) -> Self: ...

    @overload
    def __get__(
        self, instance: "_SacNested", owner: type["_SacNested"]
    ) -> Timestamp | None: ...

    def __get__(
        self, instance: "_SacNested" | None, owner: type["_SacNested"] | None = None
    ) -> Self | Timestamp | None:
        if instance is None:
            return self

        seconds = getattr(instance._parent, self._name)

        # Handle standard Python None or traditional SAC null float
        if seconds is None or seconds == -12345.0:
            return None

        return instance._ref_datetime + Timedelta(seconds=seconds)

    def __set__(self, obj: "_SacNested", value: Timestamp | None) -> None:
        if self.readonly:
            raise AttributeError(f"SAC header '{self._name}' is read-only.")

        if value is None:
            # Set to None (or -12345.0 if your SacIO requires the SAC null value)
            setattr(obj._parent, self._name, None)
        else:
            seconds = (value - obj._ref_datetime).total_seconds()
            setattr(obj._parent, self._name, seconds)


class SacTimestamps(_SacNested):
    """Helper class to access times stored in SAC headers as [`Timestamp`][pandas.Timestamp] objects.

    The `SacTimestamps` class is used to map SAC attributes in a way that
    matches pysmo types. An instance of this class is created for each
    new (parent) [`SAC`][pysmo.classes.SAC] instance to enable pysmo
    types compatibility.


    Examples:
        Relative seismogram begin time as a float vs absolute begin time
        as a [`Timestamp`][pandas.Timestamp] object.

        ```python
        >>> from pysmo.classes import SAC
        >>> sac = SAC.from_file("example.sac")
        >>>
        >>> # SAC header "B" as stored in a SAC file
        >>> sac.b
        -63.34000015258789
        >>>
        >>> # the output above is the number of seconds relative
        >>> # to the reference time and date:
        >>> sac.kzdate , sac.kztime
        ('2005-03-01', '07:24:05.500')
        >>>
        >>> # Accessing the same SAC header via a `SacTimestamps` object
        >>> # yields a corresponding Timestamp object with the absolute time:
        >>> sac.timestamps.b
        Timestamp('2005-03-01 07:23:02.159999848+0000', tz='UTC')
        >>>
        ```

        Changing timestamp values:

        ```python
        >>> from pandas import Timedelta
        >>> sac = SAC.from_file("example.sac")
        >>>
        >>> # Original value of the "B" SAC header:
        >>> sac.b
        -63.34000015258789
        >>>
        >>> # Add 30 seconds to the absolute time:
        >>> sac.timestamps.b += Timedelta(seconds=30)
        >>>
        >>> # The relative time also changes by the same amount:
        >>> sac.b
        -33.34
        >>>
        >>> # Changing b to None is not allowed (it is a required time header):
        >>> sac.timestamps.b = None
        Traceback (most recent call last):
        ...
        TypeError: SAC time header 'b' may not be None.
        >>>
        ```
    """

    b: RequiredSacTimestamp = RequiredSacTimestamp()
    """Beginning time of the independent variable."""

    e: RequiredSacTimestamp = RequiredSacTimestamp(readonly=True)
    """Ending time of the independent variable (read-only)."""

    o: OptionalSacTimestamp = OptionalSacTimestamp()
    """Event origin time."""

    a: OptionalSacTimestamp = OptionalSacTimestamp()
    """First arrival time."""

    f: OptionalSacTimestamp = OptionalSacTimestamp()
    """Fini or end of event time."""

    t0: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 0."""

    t1: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 1."""

    t2: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 2."""

    t3: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 3."""

    t4: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 4."""

    t5: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 5."""

    t6: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 6."""

    t7: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 7."""

    t8: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 8."""

    t9: OptionalSacTimestamp = OptionalSacTimestamp()
    """User defined time pick or marker 9."""


@define(kw_only=True)
class SAC(SacIO):
    """Access and modify data stored in SAC files.

    The [`SAC`][pysmo.classes.SAC] class inherits all attributes and methods
    of the [`SacIO`][pysmo.lib.io.SacIO] class, and extends it with attributes
    that allow using pysmo types. The extra attributes are themselves instances
    of "helper" classes that shouldn't be instantiated directly.

    Examples:
        SAC instances are typically created by reading a SAC file. Users
        familiar with the SAC file format can access header and data using
        the names they are used to:

        ```python
        >>> from pysmo.classes import SAC
        >>> sac = SAC.from_file("example.sac")
        >>> sac.delta
        0.019999999552965164
        >>> sac.data
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.], shape=(180000,))
        >>> sac.evla
        -31.465999603271484
        >>>
        ```

        Presenting the data in the above way is *not* compatible with pysmo
        types. For example, event coordinates are stored in the
        [`evla`][pysmo.lib.io.SacIO.evla] and [`evlo`][pysmo.lib.io.SacIO.evlo]
        attributes, which do not match the pysmo [`Location`][pysmo.Location]
        type. Renaming or aliasing `evla` to `latitude` and `evlo` to
        `longitude` would solve the problem for the event coordinates, but
        since the SAC format also specifies station coordinates
        ([`stla`][pysmo.lib.io.SacIO.stla], [`stlo`][pysmo.lib.io.SacIO.stlo])
        we still run into compatibility issues.

        In order to map these incompatible attributes to ones that can be
        used with pysmo types, we use helper classes as a way to access the
        attributes under different names that *are* compatible with pysmo
        types:

        ```python
        >>> # Import the Seismogram type to check if the nested class is compatible:
        >>> from pysmo import Seismogram
        >>>
        >>> # First verify that a SAC instance is not a pysmo Seismogram:
        >>> isinstance(sac, Seismogram)
        False
        >>> # The sac.seismogram object is, however:
        >>> isinstance(sac.seismogram, Seismogram)
        True
        >>>
        ```

        Because the SAC file format defines a large amount of header fields for
        metadata, it needs to allow for many of these to be optional. Since the
        helper classes are more specific (and intended to be used with pysmo
        types), their attributes typically may *not* be [`None`][None]:

        ```python
        >>> # No error: a SAC file doesn't have to contain event information:
        >>> sac.evla = None
        >>>
        >>> # Error: the sac.event object may not have attributes set to `None`:
        >>> sac.event.latitude = None
        Traceback (most recent call last):
        ...
        TypeError: SacEvent.latitude may not be of None type.
        >>>
        ```

    Tip:
        The [`SAC`][pysmo.classes.SAC] class directly inherits from the
        [`SacIO`][pysmo.lib.io.SacIO] class. This gives access to all
        SAC headers, ability to load from a file, download data, and so on.
        Using [`SAC`][pysmo.classes.SAC] is therefore almost always
        preferred over using [`SacIO`][pysmo.lib.io.SacIO].
    """

    seismogram: SacSeismogram = field(init=False)
    """Access data stored in the SAC object compatible with the [`Seismogram`][pysmo.Seismogram] type."""

    station: SacStation = field(init=False)
    """Access data stored in the SAC object compatible with the [`Station`][pysmo.Station] type."""

    event: SacEvent = field(init=False)
    """Access data stored in the SAC object compatible with the [`Event`][pysmo.Event] type."""

    timestamps: SacTimestamps = field(init=False)
    """Maps a SAC times such as B, E, O, T0-T9 to Timestamp objects."""

    def __attrs_post_init__(self) -> None:
        self.seismogram = SacSeismogram(parent=self)
        self.station = SacStation(parent=self)
        self.event = SacEvent(parent=self)
        self.timestamps = SacTimestamps(parent=self)
