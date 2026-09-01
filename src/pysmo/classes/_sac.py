from __future__ import annotations

import warnings
from io import BytesIO
from os import PathLike
from typing import Self, overload
from zipfile import BadZipFile, ZipFile

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import define, field, fields, setters, validators

from pysmo import Station
from pysmo._types.location import MiniLocation
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.io import SacIO
from pysmo.lib.io._sacio import SAC_OPTIONAL_TIME_HEADERS, SAC_REQUIRED_TIME_HEADERS
from pysmo.lib.validators import convert_to_utc_timestamp
from pysmo.tools.web import fetch_sac
from pysmo.typing import PositiveTimedelta, UtcTimestamp

# SacStation/SacEvent.longitude are plain properties, not attrs fields, so
# they can't attach validators via `field(validator=...)`; instead call the
# same bounds MiniLocation.longitude uses, feeding them the real attrs
# Attribute (borrowed from MiniLocation) for the error message wording.
_LONGITUDE_VALIDATORS = (validators.gt(-180.0), validators.le(180.0))
_LONGITUDE_ATTR = fields(MiniLocation).longitude


def _validate_longitude(value: float) -> None:
    for validator in _LONGITUDE_VALIDATORS:
        validator(None, _LONGITUDE_ATTR, value)


__all__ = [
    "SAC",
    "SacEvent",
    "SacSeismogram",
    "SacStation",
    "SacTimestamps",
]


def _check_seismogram_compatible(native: SacIO) -> None:
    """Raise if `native` isn't evenly-spaced time-series data.

    `SacSeismogram` always reads `native.data`/`native.delta` as if the file
    were evenly-spaced ITIME data - SacIO itself can also read spectral and
    unevenly-spaced files, but exposing those through `SAC.seismogram`
    would silently misrepresent them as a normal `Seismogram`.
    """
    if native.iftype.lower() != "time" or not native.leven:
        raise NotImplementedError(
            "SAC only supports evenly-spaced time-series data "
            + f"(IFTYPE=ITIME, LEVEN=True); got IFTYPE={native.iftype.upper()}, "
            + f"LEVEN={native.leven}. Use SacIO directly (SAC.native) for "
            + "other SAC file types."
        )


@define(kw_only=True)
class _SacNested:
    """Base class for nested SAC classes."""

    _parent: SacIO = field(repr=False, on_setattr=setters.frozen)
    """Parent SacIO instance.

    Frozen after construction: reassigning it (rather than mutating the
    referenced SacIO in place) would silently desynchronise this nested
    helper's cached reference from [`SAC.native`][pysmo.classes.SAC.native]
    and any sibling nested helper.
    """

    @property
    def _ref_datetime(self) -> UtcTimestamp:
        """The SAC file's reference date and time.

        Note: Fallback when no reference time is set
            If the SAC instance has no reference time, this function
            assumes that it is equal to `SeismogramDefaults.begin_time`.
        """

        # ref_datetime is the utc reference time in the SAC file
        if self._parent.ref_datetime is not None:
            return convert_to_utc_timestamp(self._parent.ref_datetime)

        warnings.warn(
            f"SAC object has no reference time (kzdate/kztime), assuming {SeismogramDefaults.begin_time.isoformat()}",
            RuntimeWarning,
        )
        return SeismogramDefaults.begin_time

    @overload
    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS
    ) -> UtcTimestamp: ...

    @overload
    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_OPTIONAL_TIME_HEADERS
    ) -> UtcTimestamp | None: ...

    def _get_timestamp_from_sac(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS | SAC_OPTIONAL_TIME_HEADERS
    ) -> UtcTimestamp | None:
        """Convert a SAC time header to a Timestamp."""

        seconds = getattr(self._parent, sac_time_header)

        if seconds is None:
            if isinstance(sac_time_header, SAC_REQUIRED_TIME_HEADERS):
                raise ValueError(
                    f"Required SAC header {sac_time_header!r} is missing or "
                    + f"None on {type(self).__name__}."
                )
            return None

        return self._ref_datetime + pd.Timedelta(seconds=seconds)

    @overload
    def _set_sac_from_timestamp(
        self, sac_time_header: SAC_REQUIRED_TIME_HEADERS, value: pd.Timestamp
    ) -> None: ...

    @overload
    def _set_sac_from_timestamp(
        self, sac_time_header: SAC_OPTIONAL_TIME_HEADERS, value: pd.Timestamp | None
    ) -> None: ...

    def _set_sac_from_timestamp(
        self,
        sac_time_header: SAC_REQUIRED_TIME_HEADERS | SAC_OPTIONAL_TIME_HEADERS,
        value: pd.Timestamp | None,
    ) -> None:
        """Set a SAC time header from a Timestamp."""

        if value is None:
            setattr(self._parent, sac_time_header, None)
            return

        aware_value = convert_to_utc_timestamp(value)
        seconds = (aware_value - self._ref_datetime).total_seconds()
        setattr(self._parent, sac_time_header, seconds)


@define(kw_only=True)
class SacSeismogram(_SacNested, SeismogramEndtimeMixin):
    """Helper class for SAC seismogram attributes.

    The `SacSeismogram` class maps SAC attributes to match the pysmo
    [`Seismogram`][pysmo.Seismogram] type. An instance is created for each
    new [`SAC`][pysmo.classes.SAC] instance.

    Examples:
        A SacSeismogram can be passed to any function that expects the pysmo
        [`Seismogram`][pysmo.Seismogram] type:

        ```python
        >>> from pysmo import Seismogram
        >>> from pysmo.classes import SAC
        >>>
        >>> def begin_time_isoformat(seismogram: Seismogram) -> str:
        ...     return seismogram.begin_time.isoformat()
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> begin_time_isoformat(sac.seismogram)
        '2010-02-27T06:44:06.069538+00:00'
        >>>
        ```

        Timing operations in a SAC file use a reference time, and all times
        (begin time, event origin time, picks, etc.) are relative to this
        reference time. In pysmo only absolute times are used. The example
        below shows the `begin_time` is the absolute time (in UTC) of the first
        data point:

        ```python
        >>> sac.seismogram.begin_time
        Timestamp('2010-02-27 06:44:06.069538+0000', tz='UTC')
        >>>
        ```
    """

    @property
    def data(self) -> npt.NDArray[np.floating]:
        """Seismogram data."""

        return self._parent.data

    @data.setter
    def data(self, value: npt.NDArray[np.floating]) -> None:
        self._parent.data = value

    @property
    def delta(self) -> PositiveTimedelta:
        """Sampling interval."""
        return pd.Timedelta(seconds=self._parent.delta)

    @delta.setter
    def delta(self, value: pd.Timedelta) -> None:
        if value <= pd.Timedelta(0):
            raise ValueError("delta must be a positive Timedelta.")
        self._parent.delta = value.total_seconds()

    @property
    def begin_time(self) -> UtcTimestamp:
        """Seismogram begin time."""

        return self._get_timestamp_from_sac(SAC_REQUIRED_TIME_HEADERS.b)

    @begin_time.setter
    def begin_time(self, value: pd.Timestamp) -> None:
        self._set_sac_from_timestamp(SAC_REQUIRED_TIME_HEADERS.b, value)


@define(kw_only=True)
class SacStation(_SacNested):
    """Helper class for SAC station attributes.

    The `SacStation` class maps SAC attributes to match the pysmo
    [`Station`][pysmo.Station] type. An instance is created for each new
    [`SAC`][pysmo.classes.SAC] instance.

    Examples:
        A SacStation can be passed to any function that expects the pysmo
        [`Station`][pysmo.Station] type:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo import Station
        >>>
        >>> def station_id(station: Station) -> str:
        ...     return f"{station.network}.{station.name}"
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> station_id(sac.station)
        'IU.ANMO'
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
    def name(self, value: str) -> None:
        setattr(self._parent, "kstnm", value)

    @property
    def network(self) -> str:
        """Network name or code."""

        if self._parent.knetwk is None:
            raise TypeError("SAC object network name 'knetwk' is None.")

        return self._parent.knetwk

    @network.setter
    def network(self, value: str) -> None:
        setattr(self._parent, "knetwk", value)

    @property
    def location(self) -> str:
        """Location code.

        Unlike the other station identifiers, a missing location code
        (`khole` not set) is common in real-world SAC files and is not
        treated as an error - it is returned as an empty string.
        """

        return self._parent.khole or ""

    @location.setter
    def location(self, value: str) -> None:
        setattr(self._parent, "khole", value)

    @property
    def channel(self) -> str:
        """Channel code."""

        if self._parent.kcmpnm is None:
            raise TypeError("SAC object channel code 'kcmpnm' is None.")
        return self._parent.kcmpnm

    @channel.setter
    def channel(self, value: str) -> None:
        setattr(self._parent, "kcmpnm", value)

    @property
    def latitude(self) -> int | float:
        """Station latitude."""

        if self._parent.stla is None:
            raise TypeError("SAC object station latitude 'stla' is None.")
        return self._parent.stla

    @latitude.setter
    def latitude(self, value: int | float) -> None:
        setattr(self._parent, "stla", value)

    @property
    def longitude(self) -> int | float:
        """Station longitude."""

        if self._parent.stlo is None:
            raise TypeError("SAC object station longitude 'stlo' is None.")
        return self._parent.stlo

    @longitude.setter
    def longitude(self, value: int | float) -> None:
        _validate_longitude(value)
        setattr(self._parent, "stlo", value)

    @property
    def elevation(self) -> int | float | None:
        """Station elevation in metres."""

        return self._parent.stel

    @elevation.setter
    def elevation(self, value: int | float | None) -> None:
        setattr(self._parent, "stel", value)


@define(kw_only=True)
class SacEvent(_SacNested):
    """Helper class for SAC event attributes.

    The `SacEvent` class maps SAC attributes to match the pysmo
    [`Event`][pysmo.Event] type. An instance is created for each new
    [`SAC`][pysmo.classes.SAC] instance.

    Examples:
        A SacEvent can be passed to any function that expects the pysmo
        [`Event`][pysmo.Event] type:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo import Event
        >>>
        >>> def origin_isoformat(event: Event) -> str:
        ...     return event.time.isoformat()
        ...
        >>> sac = SAC.from_file("example.sac")
        >>> origin_isoformat(sac.event)
        '2010-02-27T06:34:11.529998536+00:00'
        >>>
        ```

    Note: Event information is optional
        Not all SAC files contain event information.
    """

    @property
    def latitude(self) -> int | float:
        """Event latitude."""

        if self._parent.evla is None:
            raise TypeError("SAC object event latitude 'evla' is None.")
        return self._parent.evla

    @latitude.setter
    def latitude(self, value: int | float) -> None:
        setattr(self._parent, "evla", value)

    @property
    def longitude(self) -> int | float:
        """Event longitude."""

        if self._parent.evlo is None:
            raise TypeError("SAC object event longitude 'evlo' is None.")
        return self._parent.evlo

    @longitude.setter
    def longitude(self, value: int | float) -> None:
        _validate_longitude(value)
        setattr(self._parent, "evlo", value)

    @property
    def depth(self) -> int | float:
        """Event depth in metres (positive downward from the surface)."""

        if self._parent.evdp is None:
            raise TypeError("Sac object event depth 'evdp' is None.")
        return self._parent.evdp * 1000

    @depth.setter
    def depth(self, value: int | float) -> None:
        setattr(self._parent, "evdp", value / 1000)

    @property
    def time(self) -> UtcTimestamp:
        """Event origin time (UTC).

        Important: Fixed when iztype is "o"
            This property uses the [`SacIO.o`][pysmo.lib.io.SacIO.o] time
            header. If [`SacIO.iztype`][pysmo.lib.io.SacIO.iztype] is `"o"`,
            `SacIO.o` is the reference-time equivalence and is fixed at 0,
            so [`time`][pysmo.classes.SacEvent.time] cannot be changed
            directly in that case.
        """

        event_time = self._get_timestamp_from_sac(SAC_OPTIONAL_TIME_HEADERS.o)
        if event_time is None:
            raise TypeError("SAC object event time 'o' is None.")
        return event_time

    @time.setter
    def time(self, value: pd.Timestamp) -> None:
        self._set_sac_from_timestamp(SAC_OPTIONAL_TIME_HEADERS.o, value)


class RequiredSacTimestamp:
    """Descriptor for SAC headers that must exist and cannot be None.

    Args:
        readonly: If True, prevents modification of the header.
    """

    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly

    def __set_name__(self, owner: type[_SacNested], name: str) -> None:
        # Validates that this attribute name is a strictly required header
        self._name = SAC_REQUIRED_TIME_HEADERS(name)

    @overload
    def __get__(self, instance: None, owner: type[_SacNested]) -> Self: ...

    @overload
    def __get__(
        self, instance: _SacNested, owner: type[_SacNested]
    ) -> UtcTimestamp: ...

    def __get__(
        self, instance: _SacNested | None, owner: type[_SacNested] | None = None
    ) -> Self | UtcTimestamp:
        if instance is None:
            return self

        return instance._get_timestamp_from_sac(self._name)

    def __set__(self, obj: _SacNested, value: pd.Timestamp) -> None:
        if self.readonly:
            raise AttributeError(f"SAC header '{self._name}' is read-only.")

        obj._set_sac_from_timestamp(self._name, value)


class OptionalSacTimestamp:
    """Descriptor for SAC headers that may be missing or set to None.

    Args:
        readonly: If True, prevents modification of the header.
    """

    def __init__(self, readonly: bool = False) -> None:
        self.readonly = readonly

    def __set_name__(self, owner: type[_SacNested], name: str) -> None:
        # Validates that this attribute name is an optional header
        self._name = SAC_OPTIONAL_TIME_HEADERS(name)

    @overload
    def __get__(self, instance: None, owner: type[_SacNested]) -> Self: ...

    @overload
    def __get__(
        self, instance: _SacNested, owner: type[_SacNested]
    ) -> UtcTimestamp | None: ...

    def __get__(
        self, instance: _SacNested | None, owner: type[_SacNested] | None = None
    ) -> Self | UtcTimestamp | None:
        if instance is None:
            return self

        return instance._get_timestamp_from_sac(self._name)

    def __set__(self, obj: _SacNested, value: pd.Timestamp | None) -> None:
        if self.readonly:
            raise AttributeError(f"SAC header '{self._name}' is read-only.")

        obj._set_sac_from_timestamp(self._name, value)


class SacTimestamps(_SacNested):
    """Helper class to access times stored in SAC headers as [`Timestamp`][pandas.Timestamp] objects.

    The `SacTimestamps` class maps raw SAC time headers — relative to a
    file's own reference time — to absolute [`Timestamp`][pandas.Timestamp]
    objects. An instance of this class is created for each new
    [`SAC`][pysmo.classes.SAC] instance.

    Examples:
        Relative seismogram begin time as a float vs absolute begin time
        as a [`Timestamp`][pandas.Timestamp] object.

        ```python
        >>> from pysmo.classes import SAC
        >>> sac = SAC.from_file("example.sac")
        >>>
        >>> # SAC header "B" as stored in a SAC file
        >>> sac.native.b
        0.0005380000220611691
        >>>
        >>> # the output above is the number of seconds relative
        >>> # to the reference time and date:
        >>> sac.native.kzdate , sac.native.kztime
        ('2010-02-27', '06:44:06.069')
        >>>
        >>> # Accessing the same SAC header via a `SacTimestamps` object
        >>> # yields a corresponding Timestamp object with the absolute time:
        >>> sac.timestamps.b
        Timestamp('2010-02-27 06:44:06.069538+0000', tz='UTC')
        >>>
        ```

        Changing timestamp values:

        ```python
        >>> import pandas as pd
        >>> sac = SAC.from_file("example.sac")
        >>>
        >>> # Original value of the "B" SAC header:
        >>> sac.native.b
        0.0005380000220611691
        >>>
        >>> # Add 30 seconds to the absolute time:
        >>> sac.timestamps.b += pd.Timedelta(seconds=30)
        >>>
        >>> # The relative time also changes by the same amount:
        >>> sac.native.b
        30.000538
        >>>
        >>> # Changing b to None is not allowed (it is a required time header):
        >>> sac.timestamps.b = None
        Traceback (most recent call last):
        ...
        TypeError: ...
        >>>
        ```
    """

    __slots__ = ()

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
class SAC:
    """Access and modify data stored in SAC files.

    [`SAC`][pysmo.classes.SAC] wraps a [`SacIO`][pysmo.lib.io.SacIO] instance
    and adds attributes alongside it that allow using pysmo types. The extra
    attributes are themselves instances of "helper" classes that should not
    be instantiated directly.

    Examples:
        SAC instances are typically created by reading a SAC file:

        ```python
        >>> from pysmo.classes import SAC
        >>> sac = SAC.from_file("example.sac")
        >>> sac.seismogram.delta
        Timedelta('0 days 00:00:00.050000000')
        >>> sac.seismogram.data
        array([-47201., -47361., -47511., ..., -82144., -71072., -59960.],
              shape=(57465,))
        >>>
        ```

        Raw SAC header values are *not* compatible with pysmo types. For
        example, event coordinates are stored in the
        [`evla`][pysmo.lib.io.SacIO.evla] and [`evlo`][pysmo.lib.io.SacIO.evlo]
        headers, which do not match the pysmo [`Location`][pysmo.Location]
        type. Renaming or aliasing `evla` to `latitude` and `evlo` to
        `longitude` would solve the problem for the event coordinates, but
        since the SAC format also specifies station coordinates
        ([`stla`][pysmo.lib.io.SacIO.stla], [`stlo`][pysmo.lib.io.SacIO.stlo]),
        the same compatibility issue remains.

        The [`SAC`][pysmo.classes.SAC] class solves this with helper classes
        that map these incompatible attributes to ones compatible with pysmo
        types, accessible under different names:

        ```python
        >>> from pysmo import Seismogram
        >>>
        >>> def sample_count(seismogram: Seismogram) -> int:
        ...     return len(seismogram.data)
        ...
        >>> # A bare SAC instance is not a Seismogram: a type checker rejects
        >>> # this, and at runtime the function fails on the missing member:
        >>> sample_count(sac)
        Traceback (most recent call last):
            ...
        AttributeError: 'SAC' object has no attribute 'data'
        >>> # The sac.seismogram helper is a Seismogram:
        >>> sample_count(sac.seismogram)
        57465
        >>>
        ```

        Because the SAC file format defines a large number of header fields
        for metadata, many of them are optional. Since the helper classes
        are more specific (and intended to be used with pysmo types), their
        attributes typically may *not* be [`None`][]:

        ```python
        >>> # No error: a SAC file doesn't have to contain event information:
        >>> sac.native.evla = None
        >>>
        ```

    Tip: A curated surface, not the full header set
        [`SAC`][pysmo.classes.SAC] only exposes a small, curated surface
        directly (file I/O, and the pysmo-typed
        [`station`][pysmo.classes.SAC.station],
        [`event`][pysmo.classes.SAC.event],
        [`seismogram`][pysmo.classes.SAC.seismogram] and
        [`timestamps`][pysmo.classes.SAC.timestamps] helpers) rather than
        the full raw SAC header set. Seismogram data and sampling interval
        are available via [`seismogram`][pysmo.classes.SAC.seismogram].
        Users familiar with the SAC file format who want direct access to a
        header by its native name (e.g. `evla`, `stla`, `kstnm`) can reach
        the underlying [`SacIO`][pysmo.lib.io.SacIO] instance via
        [`SAC.native`][pysmo.classes.SAC.native].
    """

    native: SacIO = field(factory=SacIO, repr=False, on_setattr=setters.frozen)
    """The underlying [`SacIO`][pysmo.lib.io.SacIO] instance.

    This is the escape hatch for direct access to raw SAC headers by their
    native names (e.g. `SAC.native.evla`), for users familiar with the SAC file
    format who need it.

    Fixed for the lifetime of the instance: [`seismogram`][pysmo.classes.SAC.seismogram],
    [`station`][pysmo.classes.SAC.station], [`event`][pysmo.classes.SAC.event]
    and [`timestamps`][pysmo.classes.SAC.timestamps] are bound to this object
    at construction time, so reassigning it would silently orphan them. To
    load different data into an existing instance, use
    [`read`][pysmo.classes.SAC.read]/[`read_bytes`][pysmo.classes.SAC.read_bytes],
    which update this same object in place; otherwise construct a new
    [`SAC`][pysmo.classes.SAC] instance.
    """

    seismogram: SacSeismogram = field(init=False)
    """This SAC object exposed as a [`Seismogram`][pysmo.Seismogram]."""

    station: SacStation = field(init=False)
    """This SAC object exposed as a [`Station`][pysmo.Station]."""

    event: SacEvent = field(init=False)
    """This SAC object exposed as an [`Event`][pysmo.Event]."""

    timestamps: SacTimestamps = field(init=False)
    """Maps SAC time headers such as B, E, O, T0-T9 to
    [`Timestamp`][pandas.Timestamp] objects."""

    def __attrs_post_init__(self) -> None:
        self.seismogram = SacSeismogram(parent=self.native)
        self.station = SacStation(parent=self.native)
        self.event = SacEvent(parent=self.native)
        self.timestamps = SacTimestamps(parent=self.native)

    @classmethod
    def from_file(cls, filename: str | PathLike[str]) -> Self:
        """Create a new SAC instance from a SAC file.

        Args:
            filename: Name of the SAC file to read.

        Returns:
            A new SAC instance.

        Raises:
            NotImplementedError: If the file isn't evenly-spaced time-series
                data (IFTYPE=ITIME, LEVEN=True). Use
                [`SacIO.from_file`][pysmo.lib.io.SacIO.from_file] directly
                for other SAC file types.
        """
        native = SacIO.from_file(filename)
        _check_seismogram_compatible(native)
        return cls(native=native)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Create a new SAC instance from SAC file content as bytes.

        Args:
            data: Raw bytes of a SAC file.

        Returns:
            A new SAC instance.

        Raises:
            NotImplementedError: If the data isn't evenly-spaced
                time-series data (IFTYPE=ITIME, LEVEN=True). Use
                [`SacIO.from_buffer`][pysmo.lib.io.SacIO.from_buffer]
                directly for other SAC file types.
        """
        native = SacIO.from_buffer(data)
        _check_seismogram_compatible(native)
        return cls(native=native)

    def read(self, filename: str | PathLike[str]) -> None:
        """Read data and headers from a SAC file into an existing SAC instance.

        Args:
            filename: Name of the SAC file to read.

        Raises:
            NotImplementedError: If the file isn't evenly-spaced time-series
                data (IFTYPE=ITIME, LEVEN=True).
        """
        self.native.read(filename)
        _check_seismogram_compatible(self.native)

    def read_bytes(self, data: bytes) -> None:
        """Read SAC file content as bytes into an existing SAC instance.

        Args:
            data: Raw bytes of a SAC file.

        Raises:
            NotImplementedError: If the data isn't evenly-spaced
                time-series data (IFTYPE=ITIME, LEVEN=True).
        """
        self.native.read_buffer(data)
        _check_seismogram_compatible(self.native)

    def write(self, filename: str | PathLike[str]) -> None:
        """Write data and header values to a SAC file.

        Args:
            filename: Name of the SAC file to write to.
        """
        self.native.write(filename)

    @classmethod
    def from_zip(cls, archive: bytes) -> Self:
        """Create a new instance from a zip archive containing exactly one continuous SAC segment.

        Args:
            archive: Raw zip archive bytes containing exactly one SAC file
                (as returned by the FDSN dataselect web service with
                `format=sac.zip`).

        Returns:
            A new SAC instance.

        Raises:
            ValueError: If `archive` is not a valid zip archive, contains no
                members, contains more than one member (e.g. due to a data
                gap, an instrument/metadata epoch change, overlapping
                records, or a wildcarded channel/location code matching
                more than one channel), or a member cannot be parsed as a
                SAC file.

        Tip: See Also
            [`SAC.all_from_zip`][pysmo.classes.SAC.all_from_zip]: Parse
            every segment in the archive without requiring exactly one.
        """
        segments = cls.all_from_zip(archive)
        if len(segments) == 1:
            return segments[0]
        if not segments:
            raise ValueError("Zip archive contains no SAC segments.")

        segment_lines = "\n".join(
            f"  {segment.station.network}.{segment.station.name}."
            + f"{segment.station.location}.{segment.station.channel}  "
            + f"{segment.seismogram.begin_time} -- {segment.seismogram.end_time}"
            for segment in segments
        )
        raise ValueError(
            f"Zip archive contains {len(segments)} segments; "
            + "SAC.from_zip() requires exactly one continuous segment. "
            + "Use SAC.all_from_zip() to get all segments instead. "
            + f"Segments found:\n{segment_lines}"
        )

    @classmethod
    def fetch(
        cls, *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
    ) -> Self:
        """Fetch and parse a SAC seismogram from the EarthScope FDSN dataselect web service, for an absolute time window.

        For a window relative to a predicted phase arrival instead, compute
        the window yourself (e.g. with
        [`pysmo.tools.traveltime.travel_times`][], which shows exactly this
        in its own Examples) and pass the resulting *starttime*/*endtime*
        here.

        To fetch once and interpret later (e.g. offline, or without
        repeating the network request), use
        [`pysmo.tools.web.fetch_sac`][] and
        [`from_zip`][pysmo.classes.SAC.from_zip] /
        [`all_from_zip`][pysmo.classes.SAC.all_from_zip] directly instead.

        Args:
            station: Any object satisfying the [`Station`][pysmo.Station]
                protocol. Provides the network, station code, location, and
                channel for the request.
            starttime: Start of the requested time window (UTC).
            endtime: End of the requested time window (UTC).

        Returns:
            A new SAC instance.

        Raises:
            ValueError: If no waveform data is returned for the given
                window, if more than one continuous segment is returned
                (e.g. due to a data gap, an instrument/metadata epoch
                change, overlapping records, or a wildcarded channel/
                location code matching more than one channel), or if a
                returned segment cannot be parsed as a SAC file.
            urllib3.exceptions.ResponseError: If the dataselect web service
                returns an HTTP error.

        Examples:
            <!-- skip: start if(not run_real_web_requests) -->
            ```python
            >>> import pandas as pd
            >>> from pysmo import MiniStation
            >>> from pysmo.classes import SAC
            >>> station = MiniStation(
            ...     name="ANMO", network="IU", location="00", channel="LHZ",
            ...     latitude=34.945981, longitude=-106.457133,
            ... )
            >>> sac = SAC.fetch(
            ...     station=station,
            ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
            ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            ... )
            >>>
            ```
            <!-- skip: end -->
        """
        starttime = convert_to_utc_timestamp(starttime)
        endtime = convert_to_utc_timestamp(endtime)
        archive = fetch_sac(station=station, starttime=starttime, endtime=endtime)

        # dataselect returns an empty (zero-length) body, not a
        # zero-member zip archive, when a request is well-formed but
        # matches no data (HTTP 204, the FDSN default `nodata` handling) —
        # confirmed live.
        if not archive:
            raise ValueError(
                "No waveform data returned for "
                + f"{station.network}.{station.name}.{station.location}."
                + f"{station.channel} between {starttime} and {endtime}."
            )
        return cls.from_zip(archive)

    @classmethod
    def all_from_zip(cls, archive: bytes) -> list[Self]:
        """Create one instance per SAC file in a zip archive.

        Unlike [`from_zip`][pysmo.classes.SAC.from_zip], this does not
        require exactly one segment — a response covering a data gap, an
        instrument/metadata epoch change, or a wildcarded channel/location
        code returns several, which callers can inspect or merge
        themselves.

        Args:
            archive: Raw zip archive bytes, as returned by the FDSN
                dataselect web service with `format=sac.zip`.

        Returns:
            One SAC instance per member of the archive, in archive order.
            Empty if the archive has no members.

        Raises:
            ValueError: If `archive` is not a valid zip archive, or a
                member cannot be parsed as a SAC file.
        """
        try:
            with ZipFile(BytesIO(archive)) as archive_zip:
                names = archive_zip.namelist()
                segments = []
                for name in names:
                    try:
                        segments.append(cls.from_bytes(archive_zip.read(name)))
                    except Exception as error:
                        raise ValueError(
                            f"Could not parse segment {name!r} in zip archive: {error}"
                        ) from error
        except BadZipFile as error:
            raise ValueError(f"Not a valid zip archive: {error}") from error
        return segments
