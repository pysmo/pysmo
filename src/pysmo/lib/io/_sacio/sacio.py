import struct
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from os import PathLike
from pathlib import Path
from typing import Literal, Self

import numpy as np
from attrs import define

from pysmo import MiniLocation
from pysmo.tools.azdist import azimuth, backazimuth, distance

from ._lib import SacIODefaults
from ._sacio_rendered import (
    HEADER_TYPES,
    IZTYPE,
    SAC_ENUMS_DICT,
    SAC_FOOTERS,
    SAC_HEADERS,
    SAC_TIME_HEADERS,
    SacIOBase,
)

# iztype values that name an actual time header and can therefore be used as
# a zero-time reference. Excludes "unkn" (no reference) and "day" (midnight
# of the reference GMT day, which is not a header of its own).
_IZTYPE_TARGET_HEADERS = frozenset(IZTYPE.__members__) - {"unkn", "day"}


@define(kw_only=True)
class SacIO(SacIOBase):
    """
    Access SAC files in Python.

    The `SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of `SacIO` provide attributes named identically to
    header names in the SAC file format. Additional attributes may be set, but
    are not written to a SAC file (because there is no space reserved for them
    there). Class attributes with corresponding header fields in a SAC file
    (for example the begin time [`b`][pysmo.lib.io.SacIO.b]) are checked for a
    valid format before being saved in the `SacIO` instance.

    Tip:
        This class should typically never be used directly. Instead use the
        [`SAC`][pysmo.classes.SAC] class, which wraps a `SacIO` instance
        (reachable as [`SAC.native`][pysmo.classes.SAC.native]) and exposes
        it through pysmo types.

    Examples:
        Create a new instance from a file and print seismogram data:

        ```python
        >>> from pysmo.lib.io import SacIO
        >>> sac = SacIO.from_file("example.sac")
        >>> data = sac.data
        >>> data
        array([-47201., -47361., -47511., ..., -82144., -71072., -59960.],
              shape=(57465,))
        >>>
        ```

        Read the sampling rate:

        ```python
        >>> delta = sac.delta
        >>> delta
        0.05000000074505806
        >>>
        ```

        Change the sampling rate:

        ```python
        >>> newdelta = 0.05
        >>> sac.delta = newdelta
        >>> sac.delta
        0.05
        >>>
        ```
    """

    @contextmanager
    def raw(self) -> Iterator[None]:
        """Temporarily relax cross-field header restrictions on this instance.

        Some headers are restricted based on the value of another header,
        rather than by type or range alone. Writing a value that violates
        such a restriction normally raises `RuntimeError`; within this
        context, that check is skipped, so the write goes through.

        For example, [`iztype`][pysmo.lib.io.SacIO.iztype] names one time
        header (`b`, `o`, `a`, `t0`, etc.) as the zero-time reference, and
        that header is normally pinned at `0`.
        [`change_ref_time`][pysmo.lib.io.SacIO.change_ref_time] and
        [`read_buffer`][pysmo.lib.io.SacIO.read_buffer] use this context
        manager internally to move or replace the zero-time header before
        the restriction holds again.

        Note:
            Only cross-field restrictions like this are relaxed, and only
            on this instance. Other checks (type, enum membership,
            numeric bounds, string length) still apply.

        Examples:
            ```python
            >>> from pysmo.lib.io import SacIO
            >>> sac = SacIO(o=0.0, iztype="o")
            >>> with sac.raw():
            ...     sac.o = 12.0
            ...
            >>> sac.o
            12.0
            >>>
            ```
        """
        self._raw_mode = True
        try:
            yield
        finally:
            self._raw_mode = False

    @property
    def depmin(self) -> int | float | None:
        """Minimum value of dependent variable."""
        if self.npts == 0:
            return None
        return np.min(self.data).item()

    @property
    def depmax(self) -> int | float | None:
        """Maximum value of dependent variable."""
        if self.npts == 0:
            return None
        return np.max(self.data).item()

    @property
    def depmen(self) -> int | float | None:
        """Mean value of dependent variable."""
        if self.npts == 0:
            return None
        return np.mean(self.data).item()

    @property
    def e(self) -> int | float:
        """Ending value of the independent variable."""
        if self.npts == 0:
            return self.b
        return self.b + (self.npts - 1) * self.delta

    @property
    def dist(self) -> int | float:
        """Station to event distance (km)."""
        if (
            self.stla is not None
            and self.stlo is not None
            and self.evla is not None
            and self.evlo is not None
        ):
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return (
                distance(location_1=station_location, location_2=event_location) / 1000
            )
        raise TypeError("One or more coordinates are None.")

    @property
    def az(self) -> int | float:
        """Event to station azimuth (degrees)."""
        if (
            self.stla is not None
            and self.stlo is not None
            and self.evla is not None
            and self.evlo is not None
        ):
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return azimuth(location_1=station_location, location_2=event_location)
        raise TypeError("One or more coordinates are None.")

    @property
    def baz(self) -> int | float:
        """Station to event azimuth (degrees)."""
        if (
            self.stla is not None
            and self.stlo is not None
            and self.evla is not None
            and self.evlo is not None
        ):
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return backazimuth(location_1=station_location, location_2=event_location)
        raise TypeError("One or more coordinates are None.")

    @property
    def gcarc(self) -> int | float:
        """Station to event great circle arc length (degrees)."""
        if (
            self.stla is not None
            and self.stlo is not None
            and self.evla is not None
            and self.evlo is not None
        ):
            lat1, lon1 = np.deg2rad(self.stla), np.deg2rad(self.stlo)
            lat2, lon2 = np.deg2rad(self.evla), np.deg2rad(self.evlo)
            return np.rad2deg(
                np.arccos(
                    np.sin(lat1) * np.sin(lat2)
                    + np.cos(lat1) * np.cos(lat2) * np.cos(np.abs(lon1 - lon2))
                )
            )
        raise TypeError("One or more coordinates are None.")

    @property
    def xminimum(self) -> int | float | None:
        """Minimum value of X (Spectral files only)."""
        if self.nxsize == 0 or not self.nxsize:
            return None
        return np.min(self.x).item()

    @property
    def xmaximum(self) -> int | float | None:
        """Maximum value of X (Spectral files only)."""
        if self.nxsize == 0 or not self.nxsize:
            return None
        return np.max(self.x).item()

    @property
    def yminimum(self) -> int | float | None:
        """Minimum value of Y (Spectral files only)."""
        if self.nysize == 0 or not self.nysize:
            return None
        return np.min(self.y).item()

    @property
    def ymaximum(self) -> int | float | None:
        """Maximum value of Y (Spectral files only)."""
        if self.nysize == 0 or not self.nysize:
            return None
        return np.max(self.y).item()

    @property
    def npts(self) -> int:
        """Number of points per data component."""
        return np.size(self.data)

    @property
    def nxsize(self) -> int | None:
        """Spectral Length (Spectral files only)."""
        if np.size(self.x) == 0:
            return None
        return np.size(self.x)

    @property
    def nysize(self) -> int | None:
        """Spectral Width (Spectral files only)."""
        if np.size(self.y) == 0:
            return None
        return np.size(self.y)

    @property
    def lcalda(self) -> Literal[True]:
        """TRUE if DIST, AZ, BAZ, and GCARC are to be calculated from station and event coordinates.

        Note:
            Above fields are all read only properties in this class, so
            they are always calculated.
        """
        return True

    @property
    def ref_datetime(self) -> datetime | None:
        """GMT reference time and date, as a Python `datetime` object."""
        if (
            self.nzyear is None
            or self.nzjday is None
            or self.nzhour is None
            or self.nzmin is None
            or self.nzsec is None
            or self.nzmsec is None
        ):
            return None
        return datetime(
            year=self.nzyear,
            month=1,
            day=1,
            hour=self.nzhour,
            minute=self.nzmin,
            second=self.nzsec,
            microsecond=self.nzmsec * 1000,
            tzinfo=timezone.utc,
        ) + timedelta(days=self.nzjday - 1)

    @ref_datetime.setter
    def ref_datetime(self, value: datetime) -> None:
        timedelta_for_rounding = timedelta(microseconds=500)
        value += timedelta_for_rounding
        self.nzyear = value.year
        self.nzjday = value.timetuple().tm_yday
        self.nzhour = value.hour
        self.nzmin = value.minute
        self.nzsec = value.second
        self.nzmsec = int(value.microsecond / 1000)

    @property
    def kzdate(self) -> str | None:
        """ISO 8601 format of GMT reference date."""
        if self.ref_datetime is None:
            return None
        return self.ref_datetime.date().isoformat()

    @property
    def kztime(self) -> str | None:
        """Alphanumeric form of GMT reference time."""
        if self.ref_datetime is None:
            return None
        return self.ref_datetime.time().isoformat(timespec="milliseconds")

    def read(self, filename: str | PathLike) -> None:
        """Read data and headers from a SAC file into an existing SAC instance.

        Args:
            filename: Name of the sac file to read.
        """

        filename = Path(filename).resolve()

        self.read_buffer(filename.read_bytes())

    def write(self, filename: str | PathLike) -> None:
        """Writes data and header values to a SAC file.

        Args:
            filename: Name of the sacfile to write to.
        """
        with open(filename, "wb") as file_handle:
            # loop over all valid header fields and write them to the file
            for header, header_metadata in SAC_HEADERS.items():
                header_type = header_metadata.type
                header_format = header_metadata.format
                start = header_metadata.start
                header_undefined = HEADER_TYPES[header_type].undefined

                value = None
                try:
                    if hasattr(self, header):
                        value = getattr(self, header)
                except TypeError:
                    value = None

                # convert enumerated header to integer if it is not None
                if header_type == "i" and value is not None:
                    value = SAC_ENUMS_DICT[header][value]

                # set None to -12345
                if value is None:
                    value = header_undefined

                # Encode strings to bytes
                if isinstance(value, str):
                    value = value.encode()

                # write to file
                file_handle.seek(start)
                file_handle.write(struct.pack(header_format, value))

            # write data (if npts > 0)
            data_1_start = 632
            data_1_end = data_1_start + self.npts * 4
            file_handle.truncate(data_1_start)
            if self.npts > 0:
                file_handle.seek(data_1_start)
                for x in self.data:
                    file_handle.write(struct.pack("f", x))

            if self.nvhdr == 7:
                for footer, footer_metadata in SAC_FOOTERS.items():
                    undefined = -12345.0
                    start = footer_metadata.start + data_1_end
                    value = None
                    try:
                        if hasattr(self, footer):
                            value = getattr(self, footer)
                    except AttributeError:
                        value = None

                    # set None to -12345
                    if value is None:
                        value = undefined

                    # write to file
                    file_handle.seek(start)
                    file_handle.write(struct.pack("d", value))

    @classmethod
    def from_file(cls, filename: str | PathLike) -> Self:
        """Create a new SAC instance from a SAC file.

        Args:
            filename: Name of the SAC file to read.

        Returns:
            A new SacIO instance.
        """
        newinstance = cls()
        newinstance.read(filename)
        return newinstance

    @classmethod
    def from_buffer(cls, buffer: bytes) -> Self:
        """Create a new SAC instance from a SAC data buffer.

        Args:
            buffer: Buffer containing SAC file content.

        Returns:
            A new SacIO instance.
        """
        newinstance = cls()
        newinstance.read_buffer(buffer)
        return newinstance

    def read_buffer(self, buffer: bytes) -> None:
        """Read data and headers from a SAC byte buffer into an existing SAC instance.

        Args:
            buffer: Buffer containing SAC file content.
        """

        if len(buffer) < 632:
            raise EOFError()

        # Guess the file endianness first using the unused12 header field.
        # It is located at position 276 and its value should be -12345.0.
        # Try reading with little endianness
        if struct.unpack("<f", buffer[276:280])[-1] == -12345.0:
            file_byteorder = "<"
        # otherwise assume big endianness.
        else:
            file_byteorder = ">"

        # Reusing an existing instance (SAC.read/read_buffer's documented
        # reload path) must not leave it in a mix of old and new file
        # state. Suspend the zero-time guard for the whole import below:
        # otherwise a header could still carry this instance's *previous*
        # iztype-pinned value while that old iztype hasn't been overwritten
        # yet, and setting it to the new file's value would incorrectly
        # raise. iztype itself goes through object.__setattr__ throughout,
        # since it is frozen (see change_ref_time) independently of this
        # guard.
        with self.raw():
            # Reset optional headers to their defaults first, so a header
            # this file doesn't define ends up unset rather than keeping a
            # stale value from a previously loaded file.
            for header, header_metadata in SAC_HEADERS.items():
                if header_metadata.required:
                    continue
                default = getattr(SacIODefaults, header, None)
                if header == "iztype":
                    object.__setattr__(self, header, default)
                    continue
                try:
                    setattr(self, header, default)
                except AttributeError as e:
                    if "object has no setter" in str(e):
                        pass

            # Loop over all header fields and store them in the SAC object under their
            # respective private names.
            npts = 0
            for header, header_metadata in SAC_HEADERS.items():
                header_type = header_metadata.type
                header_required = header_metadata.required
                header_undefined = HEADER_TYPES[header_type].undefined
                start = header_metadata.start
                length = header_metadata.length
                end = start + length
                if end >= len(buffer):
                    continue
                content = buffer[start:end]
                value = struct.unpack(file_byteorder + header_metadata.format, content)[
                    0
                ]
                if isinstance(value, bytes):
                    # strip spaces and "\x00" chars
                    value = value.decode().rstrip(" \x00")

                # npts is read only property in this class, but is needed for reading data
                if header == "npts":
                    npts = int(value)

                # raise error if header is undefined AND required
                if value == header_undefined and header_required:
                    raise RuntimeError(
                        f"Required {header=} is undefined - invalid SAC file!"
                    )

                # skip if undefined (value == -12345...) and not required
                if value == header_undefined and not header_required:
                    continue

                # convert enumerated header to string and format others
                if header_type == "i":
                    value = SAC_ENUMS_DICT[header](value).name

                # iztype is frozen after construction (see change_ref_time), but
                # reading a file must still be able to set it from raw data.
                if header == "iztype":
                    object.__setattr__(self, header, value)
                    continue

                # SAC file has headers fields which are read only attributes in this
                # class. We skip them with this try/except.
                # TODO: This is a bit crude, should maybe be a bit more specific.
                try:
                    setattr(self, header, value)
                except AttributeError as e:
                    if "object has no setter" in str(e):
                        pass

            # Only accept IFTYPE = ITIME SAC files. Other IFTYPE use two data blocks,
            # which is something we don't support for now.
            if self.iftype.lower() != "time":
                raise NotImplementedError(
                    f"Reading SAC files with IFTYPE=(I){self.iftype.upper()} is not supported."  # noqa: E501
                )

            # Read first data block
            start = 632
            length = npts * 4
            data_end = start + length
            self.data = np.array([])
            if length > 0:
                data_end = start + length
                data_format = file_byteorder + str(npts) + "f"
                if data_end > len(buffer):
                    raise EOFError()
                content = buffer[start:data_end]
                data = struct.unpack(data_format, content)
                self.data = np.array(data)

            if self.nvhdr == 7:
                for footer, footer_metadata in SAC_FOOTERS.items():
                    undefined = -12345.0
                    length = 8
                    start = footer_metadata.start + data_end
                    end = start + length

                    if end > len(buffer):
                        raise EOFError()
                    content = buffer[start:end]

                    value = struct.unpack(file_byteorder + "d", content)[0]

                    # skip if undefined (value == -12345...)
                    if value == undefined:
                        continue

                    # SAC file has headers fields which are read only attributes in this
                    # class. We skip them with this try/except.
                    # TODO: This is a bit crude, should maybe be a bit more specific.
                    try:
                        setattr(self, footer, value)
                    except AttributeError as e:
                        if "object has no setter" in str(e):
                            pass

    def change_ref_time(self, header: str) -> None:
        """Re-point the reference time to a different time header.

        `header`'s absolute time becomes the new reference time and
        [`SacIO.iztype`][pysmo.lib.io.SacIO.iztype] is updated to match.
        [`SacIO.ref_datetime`][pysmo.lib.io.SacIO.ref_datetime] and every
        other time header are shifted by the exact same amount, so the
        absolute (UTC) time each of them represents is unchanged.

        Note:
            [`SacIO.ref_datetime`][pysmo.lib.io.SacIO.ref_datetime] only has
            millisecond precision, so the shift actually applied is rounded
            to the nearest millisecond. `header` therefore ends up within
            half a millisecond of `0`, rather than exactly `0`, whenever its
            old value was not already millisecond-aligned.

        Args:
            header: Name of the time header to make the new zero-time
                reference (e.g. `"b"`, `"o"`, `"a"`, `"t0"`, ..., `"t9"`).

        Raises:
            ValueError: If `header` cannot be used as a zero-time
                reference, if [`SacIO.ref_datetime`][pysmo.lib.io.SacIO.ref_datetime]
                is not set, or if `header`'s current value is `None`.
        """
        if header not in _IZTYPE_TARGET_HEADERS:
            raise ValueError(
                f"{header=} cannot be used as a zero-time reference "
                f"(must be one of {sorted(_IZTYPE_TARGET_HEADERS)})."
            )
        old_ref = self.ref_datetime
        if old_ref is None:
            raise ValueError(
                "Unable to change reference time: SacIO.ref_datetime is not set."
            )
        dtime = getattr(self, header)
        if dtime is None:
            raise ValueError(f"Unable to use '{header}' as a reference: it is not set.")

        # ref_datetime only has millisecond precision, so read back the
        # rounded shift it actually applied and use that for the headers.
        # This keeps every header's absolute time exactly consistent with
        # the new reference, at the cost of 'header' landing within half a
        # millisecond of 0 rather than exactly on it.
        self.ref_datetime = old_ref + timedelta(seconds=dtime)
        new_ref = self.ref_datetime
        assert new_ref is not None
        actual_dtime = (new_ref - old_ref).total_seconds()

        with self.raw():
            for time_header in SAC_TIME_HEADERS:
                try:
                    setattr(
                        self, time_header, getattr(self, time_header) - actual_dtime
                    )
                except AttributeError as e:
                    if "object has no setter" in str(e):
                        continue
                except TypeError as e:
                    if "unsupported operand type(s) for" in str(e):
                        continue

        object.__setattr__(self, "iztype", header)
