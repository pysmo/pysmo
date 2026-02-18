from ._sacio_rendered import (
    SacIOBase,
    SAC_TIME_HEADERS,
    HEADER_TYPES,
    SAC_ENUMS_DICT,
    SAC_HEADERS,
    SAC_FOOTERS,
)
from ._lib import SACIO_DEFAULTS
from pysmo import MiniLocation
from pysmo.tools.azdist import azimuth, backazimuth, distance
from attrs import define
from typing import Any, Self, Literal
from datetime import datetime, timedelta, timezone
from io import BytesIO
from zipfile import ZipFile
from os import PathLike
from pathlib import Path
import struct
import httpx
import time as _time
import numpy as np


@define(kw_only=True)
class SacIO(SacIOBase):
    """
    Access SAC files in Python.

    The `SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of `SacIO` provide attributes named identially to
    header names in the SAC file format. Additonal attributes may be set, but
    are not written to a SAC file (because there is no space reserved for them
    there). Class attributes with corresponding header fields in a SAC file
    (for example the begin time [`b`][pysmo.lib.io.SacIO.b]) are checked for a
    valid format before being saved in the `SacIO` instance.

    Warning:
        This class should typically never be used directly. Instead please
        use the [`SAC`][pysmo.classes.SAC] class, which inherits all attributes
        and methods from here.

    Examples:
        Create a new instance from a file and print seismogram data:

        ```python
        >>> from pysmo.lib.io import SacIO
        >>> sac = SacIO.from_file("example.sac")
        >>> data = sac.data
        >>> data
        array([2302., 2313., 2345., ..., 2836., 2772., 2723.], shape=(180000,))
        >>>
        ```

        Read the sampling rate:

        ```python
        >>> delta = sac.delta
        >>> delta
        0.019999999552965164
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

        Create a new instance from IRIS services:

        ```python
        >>> from pysmo.lib.io import SacIO
        >>> sac = SacIO.from_iris(net="C1",
        ... sta="VA01",
        ... cha="BHZ",
        ... loc="--",
        ... start="2021-03-22T13:00:00",
        ... duration=1 * 60 * 60,
        ... scale="AUTO",
        ... demean="true",
        ... force_single_result=True)
        >>> sac.npts
        144001
        >>>
        ```

    For each SAC(file) header field there is a corresponding attribute in this
    class. There are a lot of header fields in a SAC file, which are all called
    the same way when using `SacIO`.
    """

    @property
    def depmin(self) -> float | None:
        """Minimum value of dependent variable."""
        if self.npts == 0:
            return None
        return np.min(self.data).item()

    @property
    def depmax(self) -> float | None:
        """Maximum value of dependent variable."""
        if self.npts == 0:
            return None
        return np.max(self.data).item()

    @property
    def depmen(self) -> float | None:
        """Mean value of dependent variable."""
        if self.npts == 0:
            return None
        return np.mean(self.data).item()

    @property
    def e(self) -> float:
        """Ending value of the independent variable."""
        if self.npts == 0:
            return self.b
        return self.b + (self.npts - 1) * self.delta

    @property
    def dist(self) -> float:
        """Station to event distance (km)."""
        if self.stla and self.stlo and self.evla and self.evlo:
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return (
                distance(location_1=station_location, location_2=event_location) / 1000
            )
        raise TypeError("One or more coordinates are None.")

    @property
    def az(self) -> float:
        """Event to station azimuth (degrees)."""
        if self.stla and self.stlo and self.evla and self.evlo:
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return azimuth(location_1=station_location, location_2=event_location)
        raise TypeError("One or more coordinates are None.")

    @property
    def baz(self) -> float:
        """Station to event azimuth (degrees)."""
        if self.stla and self.stlo and self.evla and self.evlo:
            station_location = MiniLocation(latitude=self.stla, longitude=self.stlo)
            event_location = MiniLocation(latitude=self.evla, longitude=self.evlo)
            return backazimuth(location_1=station_location, location_2=event_location)
        raise TypeError("One or more coordinates are None.")

    @property
    def gcarc(self) -> float:
        """Station to event great circle arc length (degrees)."""
        if self.stla and self.stlo and self.evla and self.evlo:
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
    def xminimum(self) -> float | None:
        """Minimum value of X (Spectral files only)."""
        if self.nxsize == 0 or not self.nxsize:
            return None
        return np.min(self.x).item()

    @property
    def xmaximum(self) -> float | None:
        """Maximum value of X (Spectral files only)."""
        if self.nxsize == 0 or not self.nxsize:
            return None
        return np.max(self.x).item()

    @property
    def yminimum(self) -> float | None:
        """Minimum value of Y (Spectral files only)."""
        if self.nysize == 0 or not self.nysize:
            return None
        return np.min(self.y).item()

    @property
    def ymaximum(self) -> float | None:
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
        """Return Python datetime object of GMT reference time and date."""
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

    @classmethod
    def from_iris(
        cls,
        net: str,
        sta: str,
        cha: str,
        loc: str,
        force_single_result: bool = False,
        **kwargs: Any,
    ) -> Self | dict[str, Self] | None:
        """Create a list of SAC instances from a single IRIS
        request using the output format as "sac.zip".

        Args:
            net: Network code (e.g. "US")
            sta: Station code (e.g. "BSS")
            cha: Channel code (e.g. "BHZ")
            loc: Location code (e.g. "00")
            force_single_result: If true, the function will return a single SAC
                                object or None if the requests returns nothing.

        Returns:
            A new SacIO instance.
        """
        kwargs["net"] = net
        kwargs["sta"] = sta
        kwargs["cha"] = cha
        kwargs["loc"] = loc
        kwargs["output"] = "sac.zip"

        if isinstance(kwargs["start"], datetime):
            kwargs["start"] = kwargs["start"].isoformat()

        end = kwargs.get("end", None)
        if end is not None and isinstance(end, datetime):
            kwargs["end"] = end.isoformat()

        transport = httpx.HTTPTransport(retries=3)
        client = httpx.Client(transport=transport)
        for attempt in range(SACIO_DEFAULTS.iris_request_retries):
            response = client.get(
                SACIO_DEFAULTS.iris_base_url,
                params=kwargs,
                follow_redirects=False,
                timeout=SACIO_DEFAULTS.iris_timeout_seconds,
            )
            if (
                response.status_code == 500
                and attempt < SACIO_DEFAULTS.iris_request_retries - 1
            ):
                _time.sleep(SACIO_DEFAULTS.iris_retry_delay_seconds)
                continue
            response.raise_for_status()
            break

        zip = ZipFile(BytesIO(response.content))

        result = {}
        for name in zip.namelist():
            buffer = zip.read(name)
            sac = cls.from_buffer(buffer)
            if force_single_result:
                return sac
            result[name] = sac
        return None if force_single_result else result

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
            value = struct.unpack(file_byteorder + header_metadata.format, content)[0]
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

    def change_all_times(self, dtime: float) -> None:
        """Change all time headers by the same amount.

        Args:
            dtime: Time offset to apply.

        Warning:
            This method also changes the value for the current zero time header.
            Typically it should only be used when changing
            [`SacIO.iztype`][pysmo.lib.io.SacIO.iztype].
        """
        try:
            self._zero_time_can_be_none_zero = True
            for time_header in SAC_TIME_HEADERS:
                try:
                    setattr(self, time_header, getattr(self, time_header) + dtime)
                except AttributeError as e:
                    if "object has no setter" in str(e):
                        continue
                except TypeError as e:
                    if "unsupported operand type(s) for" in str(e):
                        continue

        finally:
            self._zero_time_can_be_none_zero = False
