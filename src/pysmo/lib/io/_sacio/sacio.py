import struct
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from os import PathLike
from pathlib import Path
from typing import Literal, Self

import numpy as np
from attrs import converters, define, field, validators

from pysmo import MiniLocation
from pysmo.tools.azdist import azimuth, backazimuth, distance

from .._atomic import atomic_write
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
    """Access SAC files in Python.

    The `SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of `SacIO` provide attributes named identically to
    header names in the SAC file format. Additional attributes may be set, but
    are not written to a SAC file (because there is no space reserved for them
    there). Class attributes with corresponding header fields in a SAC file
    (for example the begin time [`b`][pysmo.lib.io.SacIO.b]) are checked for a
    valid format before being saved in the `SacIO` instance.

    Tip: For advanced use cases only
        This class should typically never be used directly. Instead use the
        [`SAC`][pysmo.classes.SAC] class, which wraps a `SacIO` instance
        (reachable as [`SAC.native`][pysmo.classes.SAC.native]) and exposes it
        through pysmo types.

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

    sb: float | None = field(
        default=None,
        converter=converters.optional(float),
        validator=validators.optional(validators.instance_of(float)),
    )
    """Begin value of the original time series file (Stored B).

    Note: Only present in v7 spectral files
        Only present in v7 files, and only meaningful for spectral
        (IRLIM/IAMPH) files produced by a forward Fourier transform. Has no
        corresponding header field of its own; it exists only in the v7
        footer, unlike headers such as [`b`][pysmo.lib.io.SacIO.b] that also
        have a single-precision header slot.
    """

    sdelta: float | None = field(
        default=None,
        converter=converters.optional(float),
        validator=validators.optional(validators.instance_of(float)),
    )
    """Time increment in the original time series file (Stored DELTA).

    Note: Only present in v7 spectral files
        Only present in v7 files, and only meaningful for spectral
        (IRLIM/IAMPH) files produced by a forward Fourier transform. Has no
        corresponding header field of its own; it exists only in the v7
        footer, unlike headers such as [`delta`][pysmo.lib.io.SacIO.delta]
        that also have a single-precision header slot.
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
        that header cannot normally be changed.
        [`change_ref_time`][pysmo.lib.io.SacIO.change_ref_time] and
        [`read_buffer`][pysmo.lib.io.SacIO.read_buffer] use this context
        manager internally to move or replace the zero-time header before
        the restriction holds again.

        Note: Only cross-field restrictions are relaxed
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
            cos_angle = np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(
                lat2
            ) * np.cos(np.abs(lon1 - lon2))
            # Clamp: rounding can push this just past ±1, making arccos NaN.
            return np.rad2deg(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
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
        """TRUE if DIST, AZ, BAZ, and GCARC are computed from station/event coordinates.

        Note: Always calculated, never stored
            Above fields are all read only properties in this class, so
            they are always calculated.
        """
        return True

    @property
    def ref_datetime(self) -> datetime | None:
        """GMT reference time and date, as a Python `datetime` object.

        See [`datetime`][datetime.datetime].
        """
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
            tzinfo=UTC,
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

    def read(self, filename: str | PathLike[str]) -> None:
        """Read data and headers from a SAC file into an existing SAC instance.

        Args:
            filename: Name of the sac file to read.
        """

        filename = Path(filename).resolve()

        self.read_buffer(filename.read_bytes())

    def write(
        self, filename: str | PathLike[str], *, nvhdr: Literal[6, 7] | None = None
    ) -> None:
        """Write data and headers to a SAC file.

        Headers and data are always written little-endian, regardless of the
        host byte order; `read` accepts either endianness.

        The file is written in the header version given by `nvhdr`, or in
        the version of this instance ([`SacIO.nvhdr`][pysmo.lib.io.SacIO.nvhdr])
        if `nvhdr` is `None`. Version 7 adds a footer with 64-bit copies of
        `delta`, the time headers, and the event and station coordinates, so
        converting from version 6 to 7 loses nothing.

        Warning: Version 6 stores these headers as 32-bit floats
            Writing version 6 drops the footer, so these headers keep only
            32-bit precision. This applies both when converting a version 7
            instance and when writing headers changed in memory, which are
            held at 64-bit precision.

        The file is written via a temporary file in the target's directory and
        an atomic replace, so a failure mid-write cannot destroy an existing
        valid file. That directory must therefore be writable (and hold room
        for the new file alongside the old), even when overwriting an existing
        writable file. When the target already exists its mode and ownership
        are carried over to the new file; a symlink target is resolved so the
        file it points to is replaced, not the link itself.

        Args:
            filename: Name of the sacfile to write to.
            nvhdr: Header version to write. Defaults to the version of this
                instance.

        Raises:
            ValueError: If `nvhdr` is not `6`, `7` or `None`.
        """
        version = self.nvhdr if nvhdr is None else nvhdr
        if version not in (6, 7):
            raise ValueError(f"{nvhdr=} must be 6 or 7.")

        with atomic_write(filename, suffix=".sac.tmp") as tmp_name:
            with open(tmp_name, "wb") as file_handle:
                # loop over all valid header fields and write them to the file
                for header, header_metadata in SAC_HEADERS.items():
                    header_type = header_metadata.type
                    # little-endian, matching the data blocks and footers below
                    header_format = "<" + header_metadata.format
                    start = header_metadata.start
                    header_undefined = HEADER_TYPES[header_type].undefined

                    value = None
                    try:
                        if hasattr(self, header):
                            value = getattr(self, header)
                    except (AttributeError, TypeError):
                        value = None

                    if header == "nvhdr":
                        value = version

                    # convert enumerated header to integer if it is not None
                    if header_type == "i" and value is not None:
                        value = SAC_ENUMS_DICT[header][value]

                    # set None to -12345
                    if value is None:
                        value = header_undefined

                    # Encode strings to bytes
                    if isinstance(value, str):
                        value = value.encode()
                        # struct.pack silently truncates a "Ns" field to N bytes
                        # rather than raising. header_metadata.length validators
                        # (e.g. max_len) only bound the *character* count, so a
                        # string using multi-byte UTF-8 characters can still
                        # overflow the header's byte width and get corrupted on
                        # write without warning.
                        if len(value) > header_metadata.length:
                            raise ValueError(
                                f"{header!r} value {value.decode()!r} is "
                                + f"{len(value)} bytes when encoded, exceeding the "
                                + f"{header_metadata.length}-byte SAC header limit."
                            )

                    # write to file
                    file_handle.seek(start)
                    file_handle.write(struct.pack(header_format, value))

                has_second_block = self.iftype.lower() in ("rlim", "amph") or (
                    not self.leven
                )

                # write data (if npts > 0)
                data_1_start = 632
                data_1_end = data_1_start + self.npts * 4
                file_handle.truncate(data_1_start)
                if self.npts > 0:
                    file_handle.seek(data_1_start)
                    file_handle.write(np.asarray(self.data, dtype="<f4").tobytes())

                data_end = data_1_end
                if has_second_block:
                    if len(self.data2) != self.npts:
                        raise ValueError(
                            f"data2 must have the same length as data ({self.npts=}), "
                            + f"got {len(self.data2)}."
                        )
                    data_2_end = data_1_end + self.npts * 4
                    if self.npts > 0:
                        file_handle.seek(data_1_end)
                        file_handle.write(np.asarray(self.data2, dtype="<f4").tobytes())
                    data_end = data_2_end

                if version == 7:
                    for footer, footer_metadata in SAC_FOOTERS.items():
                        undefined = -12345.0
                        start = footer_metadata.start + data_end
                        value = None
                        try:
                            if hasattr(self, footer):
                                value = getattr(self, footer)
                        except (AttributeError, TypeError):
                            value = None

                        # set None to -12345
                        if value is None:
                            value = undefined

                        # write to file
                        file_handle.seek(start)
                        file_handle.write(struct.pack("<d", value))

    @classmethod
    def from_file(cls, filename: str | PathLike[str]) -> Self:
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
            raise EOFError

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
        # DELTA has no meaningful nominal value for unevenly-spaced files,
        # and real SAC writes it as undefined for them - so its "required"
        # header flag only actually holds when LEVEN is True. Peek at
        # LEVEN's raw byte before the reset/parse loops below need it,
        # since delta (word 0) is read before leven (word 105) in file
        # order.
        leven_header = SAC_HEADERS["leven"]
        leven_end = leven_header.start + leven_header.length
        file_leven = (
            struct.unpack(
                file_byteorder + leven_header.format,
                buffer[leven_header.start : leven_end],
            )[0]
            if leven_end <= len(buffer)
            else True
        )

        with self.raw():
            # Reset optional headers to their defaults first, so a header
            # this file doesn't define ends up unset rather than keeping a
            # stale value from a previously loaded file.
            for header, header_metadata in SAC_HEADERS.items():
                required = header_metadata.required and not (
                    header == "delta" and not file_leven
                )
                if required:
                    continue
                default = getattr(SacIODefaults, header, None)
                if header == "iztype":
                    object.__setattr__(self, header, default)
                    continue
                if header not in _READ_ONLY_HEADERS:
                    setattr(self, header, default)

            # sb/sdelta have no header slot of their own (only a v7-footer
            # one), so the SAC_HEADERS reset loop above never touches them.
            # Reset explicitly to avoid a previous file's footer values
            # leaking through a reused instance.
            self.sb = None
            self.sdelta = None

            # Loop over all header fields and store them in the SAC object under their
            # respective private names.
            npts = 0
            for header, header_metadata in SAC_HEADERS.items():
                header_type = header_metadata.type
                header_required = header_metadata.required and not (
                    header == "delta" and not file_leven
                )
                header_undefined = HEADER_TYPES[header_type].undefined
                start = header_metadata.start
                length = header_metadata.length
                end = start + length
                if end > len(buffer):
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

                # Logical headers have no "undefined" state distinct from
                # False, so the checks below don't apply to type "l".
                is_undefined = header_type != "l" and value == header_undefined

                # raise error if header is undefined AND required
                if is_undefined and header_required:
                    raise RuntimeError(
                        f"Required {header=} is undefined - invalid SAC file!"
                    )

                # skip if undefined (value == -12345...) and not required
                if is_undefined and not header_required:
                    continue

                # convert enumerated header to string and format others
                if header_type == "i":
                    value = SAC_ENUMS_DICT[header](value).name

                # iztype is frozen after construction (see change_ref_time), but
                # reading a file must still be able to set it from raw data.
                if header == "iztype":
                    object.__setattr__(self, header, value)
                    continue

                # nvhdr is frozen too; object.__setattr__ skips its validator.
                if header == "nvhdr":
                    if value not in (6, 7):
                        raise ValueError(
                            f"Unsupported SAC header version {value=} "
                            + "(must be 6 or 7) - invalid SAC file!"
                        )
                    object.__setattr__(self, header, value)
                    continue

                # SAC file has headers fields which are read only attributes
                # in this class (computed rather than stored). Skip them.
                if header not in _READ_ONLY_HEADERS:
                    setattr(self, header, value)

            # Spectral files (IRLIM/IAMPH) and unevenly-spaced data (LEVEN =
            # False, which IXY implies) carry a second NPTS-length data
            # section straight after the first.
            has_second_block = self.iftype.lower() in ("rlim", "amph") or (
                not self.leven
            )

            # Read first data block
            start = 632
            length = npts * 4
            data_end = start + length
            self.data = np.array([])
            self.data2 = np.array([])
            if length > 0:
                data_end = start + length
                data_format = file_byteorder + str(npts) + "f"
                if data_end > len(buffer):
                    raise EOFError
                content = buffer[start:data_end]
                data = struct.unpack(data_format, content)
                self.data = np.array(data)

                if has_second_block:
                    block2_start = data_end
                    block2_end = block2_start + length
                    if block2_end > len(buffer):
                        raise EOFError
                    content = buffer[block2_start:block2_end]
                    data2 = struct.unpack(data_format, content)
                    self.data2 = np.array(data2)
                    data_end = block2_end

            if self.nvhdr == 7:
                for footer, footer_metadata in SAC_FOOTERS.items():
                    undefined = -12345.0
                    length = 8
                    start = footer_metadata.start + data_end
                    end = start + length

                    if end > len(buffer):
                        raise EOFError
                    content = buffer[start:end]

                    value = struct.unpack(file_byteorder + "d", content)[0]

                    # skip if undefined (value == -12345...)
                    if value == undefined:
                        continue

                    # SAC file has headers fields which are read only
                    # attributes in this class (computed rather than
                    # stored). Skip them.
                    if footer not in _READ_ONLY_HEADERS:
                        setattr(self, footer, value)

    def change_ref_time(self, header: str, *, shift_samples: bool = False) -> float:
        """Move the reference time to the time of a time header.

        The reference time ([`SacIO.ref_datetime`][pysmo.lib.io.SacIO.ref_datetime])
        only has millisecond precision. It is therefore set to the whole
        millisecond nearest to the absolute time of `header`. The distance
        between the two is the remainder `r`, which is returned:

        ```
        r = (absolute time of header) - (new reference time)
        ```

        with `|r| <= 0.0005` seconds. The `shift_samples` argument decides
        how `r` is handled:

        - `shift_samples=False` (default): all time headers are shifted by the
          same amount as the reference time. Every absolute time, including
          those of the samples, is unchanged, and `header` ends up at `r`
          instead of `0`.
        - `shift_samples=True`: `header` is set to exactly `0`, matching SAC's
          `chnhdr allt`. All other time headers are shifted by the same
          amount, so every absolute time, including those of the samples,
          moves by `-r`.

        In both cases the time headers keep their positions relative to each
        other and to the samples.

        Note: Setting `iztype`
            [`SacIO.iztype`][pysmo.lib.io.SacIO.iztype] is set to `header`
            only if `header` ends up at `0`. This is always the case with
            `shift_samples=True`. With `shift_samples=False`, it is the case
            only when `r` is within the storage precision of the time headers
            (float32 if [`SacIO.nvhdr`][pysmo.lib.io.SacIO.nvhdr] is `6`,
            float64 if it is `7`). `header` is then set to exactly `0` and
            `0.0` is returned. Otherwise `iztype` is set to `"unkn"`.

        Args:
            header: Name of the time header to use as the new reference
                (e.g. `"b"`, `"o"`, `"a"`, `"t0"`, ..., `"t9"`).
            shift_samples: Set `header` to exactly `0` by moving all
                absolute times, including those of the samples, by `-r`.

        Returns:
            The remainder `r` in seconds. With `shift_samples=False` this is
                the new value of `header`; with `shift_samples=True` all
                absolute times moved by `-r`.

        Raises:
            ValueError: If `header` cannot be used as a reference, if
                [`SacIO.ref_datetime`][pysmo.lib.io.SacIO.ref_datetime] is not
                set, or if the value of `header` is `None`.

        Examples:
            The begin time of `example.sac` is not on a whole millisecond.
            By default the remainder stays in `b`, and `iztype` becomes
            `"unkn"`:

            ```python
            >>> from pysmo.lib.io import SacIO
            >>> sac = SacIO.from_file("example.sac")
            >>> r = sac.change_ref_time("b")
            >>> round(r, 6)
            -0.000462
            >>> sac.b == r
            True
            >>> sac.iztype
            'unkn'
            >>>
            ```

            With `shift_samples=True`, `b` becomes `0` and all absolute
            times move by `-r` (here 0.462 ms later):

            ```python
            >>> sac = SacIO.from_file("example.sac")
            >>> r = sac.change_ref_time("b", shift_samples=True)
            >>> round(r, 6)
            -0.000462
            >>> sac.b, sac.iztype
            (0.0, 'b')
            >>>
            ```
        """
        if header not in _IZTYPE_TARGET_HEADERS:
            raise ValueError(
                f"{header=} cannot be used as a zero-time reference "
                + f"(must be one of {sorted(_IZTYPE_TARGET_HEADERS)})."
            )
        old_ref = self.ref_datetime
        if old_ref is None:
            raise ValueError(
                "Unable to change reference time: SacIO.ref_datetime is not set."
            )
        dtime = getattr(self, header)
        if dtime is None:
            raise ValueError(f"Unable to use '{header}' as a reference: it is not set.")

        # Round to whole ms here: timedelta(seconds=dtime) would first round
        # to µs, and the ref_datetime setter then rounds again to ms.
        self.ref_datetime = old_ref + timedelta(milliseconds=round(dtime * 1000))
        new_ref = self.ref_datetime
        assert new_ref is not None
        actual_dtime = (new_ref - old_ref).total_seconds()
        remainder = dtime - actual_dtime

        # A remainder within the storage precision of the time headers is
        # treated as zero. Not when shifting samples: they really move by r.
        if self.nvhdr == 6:
            tolerance = float(np.spacing(np.float32(abs(dtime)))) / 2
        else:
            tolerance = 4 * float(np.spacing(abs(dtime)))
        if not shift_samples and abs(remainder) <= tolerance:
            remainder = 0.0

        shift = dtime if shift_samples else actual_dtime

        with self.raw():
            for time_header in SAC_TIME_HEADERS:
                if time_header in _READ_ONLY_HEADERS:
                    continue
                current = getattr(self, time_header)
                if current is None:
                    continue
                setattr(self, time_header, current - shift)
            if remainder == 0.0:
                setattr(self, header, 0.0)

        is_zero = shift_samples or remainder == 0.0
        object.__setattr__(self, "iztype", header if is_zero else "unkn")
        return remainder


def _is_settable(name: str) -> bool:
    """Whether `setattr(SacIO(), name, ...)` would succeed.

    True for stored attrs fields. False for computed `@property` attributes
    with no setter, and for header/footer names with no corresponding
    attribute at all (the "unused"/"internal" reserved header words, which
    are deliberately excluded from field generation).
    """
    member = getattr(SacIO, name, None)
    if member is None:
        return False
    if isinstance(member, property):
        return member.fset is not None
    return True


# Header/footer names read_buffer()/change_ref_time() must skip rather than
# setattr. Built by introspection rather than hardcoded so it can't drift
# out of sync with the actual property/field definitions above.
_READ_ONLY_HEADERS = frozenset(
    name for name in {**SAC_HEADERS, **SAC_FOOTERS} if not _is_settable(name)
)
