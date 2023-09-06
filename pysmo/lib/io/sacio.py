from pysmo.lib.exceptions import SacHeaderUndefined
from pysmo.lib.functions import _azdist
from pysmo.lib.defaults import SACIO_DEFAULTS
try:
    from typing import Any, Self  # py311+
except ImportError:
    from typing import Any
    from typing_extensions import Self  # py310
from pydantic.dataclasses import dataclass
from pydantic import (
    FieldValidationInfo,
    ValidationError,
    field_validator,
    Field,
    ConfigDict,
    computed_field
)
import struct
import datetime
import io
import os
import requests
import yaml
import urllib.parse
import zipfile
import warnings
import numpy as np


# Read yaml file with dictionaries describing SAC headers
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _HEADER_DEFS: dict = yaml.safe_load(stream)

# Dictionary of header types (default values etc)
HEADER_TYPES: dict = _HEADER_DEFS.pop('header_types')
# Dictionary of header fields (format, type, etc)
HEADER_FIELDS: dict = _HEADER_DEFS.pop('header_fields')
# Dictionary of enumerated headers (to convert int to str).
ENUM_DICT: dict = _HEADER_DEFS.pop('enumerated_header_values')


@dataclass(config=ConfigDict(
    arbitrary_types_allowed=True,  # needed for numpy.ndarray
    validate_assignment=True,      # check at runtime
    ))
class SacIO:
    """
    The `SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of `SacIO` provide attributes named identially to
    header names in the SAC file format. Additonal attributes may be set, but are
    not written to a SAC file (because there is no space reserved for them there).
    Class attributes with corresponding header fields in a SAC file (for example the
    begin time `b`) are checked for a valid format before being saved in the
    `SacIO` instance.

    Warning:
        This class should typically never be used directly. Instead please
        use the [SAC][pysmo.classes.sac.SAC] class, which inherits all
        attributes and methods from here.

    Examples:
        Create a new instance from a file and print seismogram data:

        >>> from pysmo.lib.io import SacIO
        >>> my_sac = SacIO.from_file('testfile.sac')
        >>> data = my_sac.data
        >>> data
        array([-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, ...

        Read the sampling rate:

        >>> delta = my_sac.delta
        >>> delta
        0.019999999552965164

        Change the sampling rate:

        >>> newdelta = 0.05
        >>> my_sac.delta = newdelta
        >>> my_sac.delta
        0.05

        Create a new instance from IRIS services:

        >>> from pysmo.lib.io import SacIO
        >>> my_sac = SacIO.from_iris(
        >>>             net="C1",
        >>>             sta="VA01",
        >>>             cha="BHZ",
        >>>             loc="--",
        >>>             start="2021-03-22T13:00:00",
        >>>             duration=1 * 60 * 60,
        >>>             scale="AUTO",
        >>>             demean="true",
        >>>             force_single_result=True)
        >>> my_sac.npts
        144001

    For each SAC(file) header field there is a corresponding attribute in this class.
    There are a lot of header fields in a SAC file, which are all called the
    same way when using `SAC`.

    Attributes:
        delta: Increment between evenly spaced samples (nominal value).
        depmin: Minimum value of dependent variable.
        depmax: Maximum value of dependent variable.
        scale: Multiplying scale factor for dependent variable (not currently used).
        odelta: Observed increment if different from nominal value.
        b: Beginning value of the independent variable.
        e: Ending value of the independent variable.
        o: Event origin time (seconds relative to reference time).
        a: First arrival time (seconds relative to reference time).
        fmt: Internal.
        t0: User defined time pick or marker 0 (seconds relative to reference time).
        t1: User defined time pick or marker 1 (seconds relative to reference time).
        t2: User defined time pick or marker 2 (seconds relative to reference time).
        t3: User defined time pick or marker 3 (seconds relative to reference time).
        t4: User defined time pick or marker 4 (seconds relative to reference time).
        t5: User defined time pick or marker 5 (seconds relative to reference time).
        t6: User defined time pick or marker 6 (seconds relative to reference time).
        t7: User defined time pick or marker 7 (seconds relative to reference time).
        t8: User defined time pick or marker 8 (seconds relative to reference time).
        t9: User defined time pick or marker 9 (seconds relative to reference time).
        f: Fini or end of event time (seconds relative to reference time).
        resp0: Instrument response parameter 0 (not currently used).
        resp1: Instrument response parameter 1 (not currently used).
        resp2: Instrument response parameter 2 (not currently used).
        resp3: Instrument response parameter 3 (not currently used).
        resp4: Instrument response parameter 4 (not currently used).
        resp5: Instrument response parameter 5 (not currently used).
        resp6: Instrument response parameter 6 (not currently used).
        resp7: Instrument response parameter 7 (not currently used).
        resp8: Instrument response parameter 8 (not currently used).
        resp9: Instrument response parameter 9 (not currently used).
        stla: Station latitude (degrees, north positive).
        stlo: Station longitude (degrees, east positive).
        stel: Station elevation above sea level (meters).
        stdp: Station depth below surface (meters).
        evla: Event latitude (degrees, north positive).
        evlo: Event longitude (degrees, east positive).
        evel: Event elevation (meters).
        evdp: Event depth below surface (kilometers -- previously meters).
        mag: Event magnitude.
        user0: User defined variable storage area.
        user1: User defined variable storage area.
        user2: User defined variable storage area.
        user3: User defined variable storage area.
        user4: User defined variable storage area.
        user5: User defined variable storage area.
        user6: User defined variable storage area.
        user7: User defined variable storage area.
        user8: User defined variable storage area.
        user9: User defined variable storage area.
        dist: Station to event distance (km).
        az: Event to station azimuth (degrees).
        baz: Station to event azimuth (degrees).
        gcarc: Station to event great circle arc length (degrees).
        sb: Internal.
        sdelta: Internal.
        depmen: Mean value of dependent variable.
        cmpaz: Component azimuth (degrees clockwise from north).
        cmpinc: Component incident angle (degrees from vertical).
        xminimum: Minimum value of X (Spectral files only).
        xmaximum: Maximum value of X (Spectral files only).
        yminimum: Minimum value of Y (Spectral files only).
        ymaximum: Maximum value of Y (Spectral files only).
        unused6: Unused.
        unused7: Unused.
        unused8: Unused.
        unused9: Unused.
        unused10: Unused.
        unused11: Unused.
        unused12: Unused.
        nzyear: GMT year corresponding to reference (zero) time in file.
        nzjday: GMT julian day.
        nzhour: GMT hour.
        nzmin: GMT minute.
        nzsec: GMT second.
        nzmsec: GMT millisecond.
        nvhdr: Header version number.
        norid: Origin ID (CSS 3.0).
        nevid: Event ID (CSS 3.0).
        npts: Number of points per data component.
        nsnpts: Internal.
        nwfid: Waveform ID (CSS 3.0).
        nxsize: Spectral Length (Spectral files only).
        nysize: Spectral Length (Spectral files only).
        unused15: Unused.
        iftype: Type of file.
        idep: Type of dependent variable.
        iztype: Reference time equivalence.
        unused16: Unused.
        iinst: Type of recording instrument.
        istreg: Station geographic region.
        ievreg: Event geographic region.
        ievtyp: Type of event.
        iqual: Quality of data.
        isynth: Synthetic data flag.
        imagtyp: Magnitude type.
        imagsrc: Source of magnitude information.
        unused19: Unused.
        unused20: Unused.
        unused21: Unused.
        unused22: Unused.
        unused23: Unused.
        unused24: Unused.
        unused25: Unused.
        unused26: Unused.
        leven: TRUE if data is evenly spaced.
        lpspol: TRUE if station components have a positive polarity (left-hand rule).
        lovrok: TRUE if it is okay to overwrite this file on disk.
        lcalda: TRUE if DIST, AZ, BAZ, and GCARC are to be calculated from station and event coordinates.
        unused27: Unused.
        kstnm: Station name.
        kevnm: Event name.
        khole: Nuclear: hole identifier; Other: location identifier.
        ko: Event origin time identification.
        ka: First arrival time identification.
        kt0: User defined time pick identification.
        kt1: User defined time pick identification.
        kt2: User defined time pick identification.
        kt3: User defined time pick identification.
        kt4: User defined time pick identification.
        kt5: User defined time pick identification.
        kt6: User defined time pick identification.
        kt7: User defined time pick identification.
        kt8: User defined time pick identification.
        kt9: User defined time pick identification.
        kf: Fini identification.
        kuser0: User defined variable storage area.
        kuser1: User defined variable storage area.
        kuser2: User defined variable storage area.
        kcmpnm: Channel name. SEED volumes use three character names, and the third is the component/orientation.
                For horizontals, the current trend is to use 1 and 2 instead of N and E.
        knetwk: Name of seismic network.
        kdatrd: Date data was read onto computer.
        kinst: Generic name of recording instrument.
    """

    b: float = SACIO_DEFAULTS.b
    delta: float = SACIO_DEFAULTS.delta
    odelta: float | None = None
    scale: float | None = None
    o: float | None = None
    a: float | None = None
    fmt: float | None = None
    t0: float | None = None
    t1: float | None = None
    t2: float | None = None
    t3: float | None = None
    t4: float | None = None
    t5: float | None = None
    t6: float | None = None
    t7: float | None = None
    t8: float | None = None
    t9: float | None = None
    f: float | None = None
    resp0: float | None = None
    resp1: float | None = None
    resp2: float | None = None
    resp3: float | None = None
    resp4: float | None = None
    resp5: float | None = None
    resp6: float | None = None
    resp7: float | None = None
    resp8: float | None = None
    resp9: float | None = None
    stla: float | None = Field(default=None, ge=-90, le=90)
    stlo: float | None = Field(default=None, gt=-180, le=180)
    stel: float | None = None
    stdp: float | None = None
    evla: float | None = Field(default=None, ge=-90, le=90)
    evlo: float | None = Field(default=None, gt=-180, le=180)
    evel: float | None = None
    evdp: float | None = None
    mag: float | None = None
    user0: float | None = None
    user1: float | None = None
    user2: float | None = None
    user3: float | None = None
    user4: float | None = None
    user5: float | None = None
    user6: float | None = None
    user7: float | None = None
    user8: float | None = None
    user9: float | None = None
    sb: float | None = None
    sdelta: float | None = None
    cmpaz: float | None = None
    cmpinc: float | None = None
    unused6: float | None = None
    unused7: float | None = None
    unused8: float | None = None
    unused9: float | None = None
    unused10: float | None = None
    unused11: float | None = None
    unused12: float | None = None
    nzyear: int | None = None
    nzjday: int | None = None
    nzhour: int | None = None
    nzmin: int | None = None
    nzsec: int | None = None
    nzmsec: int | None = None
    nvhdr: int = SACIO_DEFAULTS.nvhdr
    norid: int | None = None
    nevid: int | None = None
    nsnpts: int | None = None
    nwfid: int | None = None
    unused15: int | None = None
    iftype: str = SACIO_DEFAULTS.iftype
    idep: str = SACIO_DEFAULTS.idep
    iztype: str = SACIO_DEFAULTS.iztype
    unused16: str | None = None
    iinst: str | None = None
    istreg: str | None = None
    ievreg: str | None = None
    ievtyp: str = SACIO_DEFAULTS.ievtyp
    iqual: str | None = None
    isynth: str | None = None
    imagtyp: str | None = None
    imagsrc: str | None = None
    unused19: str | None = None
    unused20: str | None = None
    unused21: str | None = None
    unused22: str | None = None
    unused23: str | None = None
    unused24: str | None = None
    unused25: str | None = None
    unused26: str | None = None
    # TODO: Unevenly spaced data
    leven: bool = SACIO_DEFAULTS.leven
    lpspol: bool | None = None
    lovrok: bool | None = None
    unused27: bool | None = None
    kstnm: str | None = Field(default=None, max_length=8)
    kevnm: str | None = Field(default=None, max_length=16)
    khole: str | None = Field(default=None, max_length=8)
    ko: str | None = Field(default=None, max_length=8)
    ka: str | None = Field(default=None, max_length=8)
    kt0: str | None = Field(default=None, max_length=8)
    kt1: str | None = Field(default=None, max_length=8)
    kt2: str | None = Field(default=None, max_length=8)
    kt3: str | None = Field(default=None, max_length=8)
    kt4: str | None = Field(default=None, max_length=8)
    kt5: str | None = Field(default=None, max_length=8)
    kt6: str | None = Field(default=None, max_length=8)
    kt7: str | None = Field(default=None, max_length=8)
    kt8: str | None = Field(default=None, max_length=8)
    kt9: str | None = Field(default=None, max_length=8)
    kf: str | None = Field(default=None, max_length=8)
    kuser0: str | None = Field(default=None, max_length=8)
    kuser1: str | None = Field(default=None, max_length=8)
    kuser2: str | None = Field(default=None, max_length=8)
    kcmpnm: str | None = Field(default=None, max_length=8)
    knetwk: str | None = Field(default=None, max_length=8)
    kdatrd: str | None = Field(default=None, max_length=8)
    kinst: str | None = Field(default=None, max_length=8)
    data: np.ndarray = Field(default_factory=lambda: np.array([]))
    x: np.ndarray = Field(default_factory=lambda: np.array([]))
    y: np.ndarray = Field(default_factory=lambda: np.array([]))

    @computed_field  # type: ignore[misc]
    @property
    def depmin(self) -> float | None:
        if self.npts == 0:
            return None
        return np.min(self.data)

    @computed_field  # type: ignore[misc]
    @property
    def depmax(self) -> float | None:
        if self.npts == 0:
            return None
        return np.max(self.data)

    @computed_field  # type: ignore[misc]
    @property
    def depmen(self) -> float | None:
        if self.npts == 0:
            return None
        return np.mean(self.data)

    @computed_field  # type: ignore[misc]
    @property
    def e(self) -> float:
        if self.npts == 0:
            return self.b
        return self.b + (self.npts - 1) * self.delta

    @computed_field  # type: ignore[misc]
    @property
    def dist(self) -> float:
        if self.stla and self.stlo and self.evla and self.evlo:
            return _azdist(lat1=self.stla, lon1=self.stlo, lat2=self.evla, lon2=self.evlo)[2] / 1000
        raise SacHeaderUndefined("One or more coordinates are None.")

    @computed_field  # type: ignore[misc]
    @property
    def az(self) -> float:
        if self.stla and self.stlo and self.evla and self.evlo:
            return _azdist(lat1=self.stla, lon1=self.stlo, lat2=self.evla, lon2=self.evlo)[0]
        raise SacHeaderUndefined("One or more coordinates are None.")

    @computed_field  # type: ignore[misc]
    @property
    def baz(self) -> float:
        if self.stla and self.stlo and self.evla and self.evlo:
            return _azdist(lat1=self.stla, lon1=self.stlo, lat2=self.evla, lon2=self.evlo)[1]
        raise SacHeaderUndefined("One or more coordinates are None.")

    @computed_field  # type: ignore[misc]
    @property
    def gcarc(self) -> float:
        if self.stla and self.stlo and self.evla and self.evlo:
            lat1, lon1 = np.deg2rad(self.stla), np.deg2rad(self.stlo)
            lat2, lon2 = np.deg2rad(self.evla), np.deg2rad(self.evlo)
            return np.rad2deg(np.arccos(np.sin(lat1) * np.sin(lat2) + np.cos(lat1)
                              * np.cos(lat2) * np.cos(np.abs(lon1 - lon2))))
        raise SacHeaderUndefined("One or more coordinates are None.")

    @computed_field  # type: ignore[misc]
    @property
    def xminimum(self) -> float | None:
        if self.nxsize == 0 or not self.nxsize:
            return None
        return float(np.min(self.x))

    @computed_field  # type: ignore[misc]
    @property
    def xmaximum(self) -> float | None:
        if self.nxsize == 0 or not self.nxsize:
            return None
        return np.max(self.x)

    @computed_field  # type: ignore[misc]
    @property
    def yminimum(self) -> float | None:
        if self.nysize == 0 or not self.nysize:
            return None
        return np.min(self.y)

    @computed_field  # type: ignore[misc]
    @property
    def ymaximum(self) -> float | None:
        if self.nysize == 0 or not self.nysize:
            return None
        return np.max(self.y)

    @computed_field  # type: ignore[misc]
    @property
    def npts(self) -> int:
        return np.size(self.data)

    @computed_field  # type: ignore[misc]
    @property
    def nxsize(self) -> float | None:
        if np.size(self.x) == 0:
            return None
        return np.size(self.x)

    @computed_field  # type: ignore[misc]
    @property
    def nysize(self) -> float | None:
        if np.size(self.y) == 0:
            return None
        return np.size(self.y)

    @computed_field  # type: ignore[misc]
    @property
    def lcalda(self) -> bool:
        # all distances and bearings are always calculated...
        return True

    @field_validator("iftype", "idep", "iztype", "ievtype", "iqual", "isynth", "imagtyp", "imagsrc")
    @classmethod
    def validate_enumerated_header(cls, value: str, info: FieldValidationInfo) -> str:
        if value and value not in HEADER_FIELDS[info.field_name]["allowed_vals"].keys():
            raise ValueError(f"Invalid {value=} for {info.field_name}. Must be one of " +
                             f"{list(HEADER_FIELDS[info.field_name]['allowed_vals'].keys())}.")
        return value

    def read(self, filename: str) -> None:
        """Read data and header values from a SAC file into an existing SAC instance.

        Parameters:
            filename: Name of the sac file to read.
        """

        with open(filename, 'rb') as file_handle:
            self.read_buffer(file_handle.read())

    def read_buffer(self, buffer: bytes) -> None:
        """Read data and header values from a SAC byte buffer into an existing SAC instance.

        Parameters:
            buffer: Buffer containing SAC file content.
        """

        if len(buffer) < 632:
            raise EOFError()

        # Guess the file endianness first using the unused12 header field.
        # It is located at position 276 and its value should be -12345.0.
        # Try reading with little endianness
        if struct.unpack('<f', buffer[276:280])[-1] == -12345.0:
            file_byteorder = '<'
        # otherwise assume big endianness.
        else:
            file_byteorder = '>'

        # Reverse ENUM_DICT so that we can look up the string from the int
        enum_dict_reversed = {v: k for k, v in ENUM_DICT.items()}

        # Loop over all header fields and store them in the SAC object under their
        # respective private names.
        npts = 0
        for header, header_dict in HEADER_FIELDS.items():
            header_type = header_dict["header_type"]
            header_start = header_dict["start"]
            header_length = header_dict.get("length", HEADER_TYPES[header_type]["length"])
            header_format = header_dict.get("format", HEADER_TYPES[header_type]["format"])
            header_undefined = HEADER_TYPES[header_type]["undefined"]
            end = header_start + header_length
            if end >= len(buffer):
                continue
            content = buffer[header_start:end]
            value = struct.unpack(file_byteorder + header_format, content)[0]
            if isinstance(value, bytes):
                # strip spaces and "\x00" chars
                value = value.decode().rstrip(" \x00")

            # npts is read only property in this class, but is needed for reading data
            if header == "npts":
                npts = int(value)

            # skip if undefined (value == -12345...)
            if value == header_undefined:
                continue

            # convert enumerated header to string and format others
            if header_type == "i":
                value = enum_dict_reversed[value]

            # SAC file has headers fields which are read only attributes in this
            # class. We skip them with this try/except.
            # TODO: This is a bit crude, should maybe be a bit more specific.
            try:
                setattr(self, header, value)
            except ValidationError as e:
                if "Object has no attribute" in str(e):
                    pass

        # Only accept IFTYPE = ITIME SAC files. Other IFTYPE use two data blocks, which is something
        # we don't support.
        if self.iftype.lower() != 'time':
            raise NotImplementedError(f"Reading SAC files with IFTYPE=(I){self.iftype.upper()} is not supported.")

        # Read first data block
        start = 632
        length = npts * 4
        self.data = np.array([])
        if length > 0:
            end = start + length
            data_format = file_byteorder + str(npts) + 'f'
            if end > len(buffer):
                raise EOFError()
            content = buffer[start:end]
            data = struct.unpack(data_format, content)
            self.data = np.array(data)

        # TODO: implement reading and writing footer with double precision values.
        # Warn users for now that footer is not read in case of SAC header version 7.
        if self.nvhdr == 7:
            warnings.warn(f"SAC header version {self.nvhdr} not implemented. Reverting to version 6")
            self.nvhdr = 6

    @classmethod
    def from_file(cls, filename: str) -> Self:
        """Create a new SAC instance from a SAC file.

        Parameters:
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

        Parameters:
            buffer: Buffer containing SAC file content.

        Returns:
            A new SacIO instance.
        """
        newinstance = cls()
        newinstance.read_buffer(buffer)
        return newinstance

    @classmethod
    def from_iris(cls, net: str, sta: str, cha: str, loc: str, force_single_result: bool = False,
                  **kwargs: Any) -> Self | dict[str, Self] | None:
        """Create a list of SAC instances from a single IRIS
        request using the output format as "sac.zip".

        Parameters:
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

        if isinstance(kwargs["start"], datetime.datetime):
            kwargs["start"] = kwargs["start"].isoformat()

        end = kwargs.get("end", None)
        if end is not None and isinstance(end, datetime.datetime):
            kwargs["end"] = end.isoformat()

        base = "https://service.iris.edu/irisws/timeseries/1/query"
        params = urllib.parse.urlencode(kwargs, doseq=False)
        url = f"{base}?{params}"
        response = requests.get(url)
        if not response:
            raise ValueError(response.content.decode("utf-8"))
        zip = zipfile.ZipFile(io.BytesIO(response.content))
        result = {}
        for name in zip.namelist():
            buffer = zip.read(name)
            sac = cls.from_buffer(buffer)
            if force_single_result:
                return sac
            result[name] = sac
        return None if force_single_result else result

    def write(self, filename: str) -> None:
        """Writes data and header values to a SAC file.

        Parameters:
            filename: Name of the sacfile to write to.
        """
        with open(filename, 'wb') as file_handle:
            # loop over all valid header fields and write them to the file
            for header, header_dict in HEADER_FIELDS.items():
                header_type = header_dict["header_type"]
                header_format = header_dict.get("format", HEADER_TYPES[header_type]["format"])
                header_undefined = HEADER_TYPES[header_type]["undefined"]

                value = None
                try:
                    value = getattr(self, header)
                except SacHeaderUndefined:
                    value = None

                # convert enumerated header to integer if it is not None
                if header_type == "i" and value:
                    value = ENUM_DICT[value]

                # set None to -12345
                if not value:
                    value = header_undefined

                # Encode strings to bytes
                if isinstance(value, str):
                    value = value.encode()

                # write to file
                file_handle.seek(header_dict.get('start'))
                file_handle.write(struct.pack(header_format, value))

            # write data (if npts > 0)
            start1 = 632
            file_handle.truncate(start1)
            if self.npts > 0:
                file_handle.seek(start1)
                for x in self.data:
                    file_handle.write(struct.pack('f', x))

    @property
    def kzdate(self) -> str | None:
        """
        Returns:
            ISO 8601 format of GMT reference date.
        """
        if self.nzyear is None or self.nzjday is None:
            return None
        _kzdate = datetime.date(self.nzyear, 1, 1) + datetime.timedelta(self.nzjday - 1)
        return _kzdate.isoformat()

    @property
    def kztime(self) -> str | None:
        """
        Returns:
            Alphanumeric form of GMT reference time.
        """
        if self.nzhour is None or self.nzmin is None or self.nzsec is None or self.nzmsec is None:
            return None
        _kztime = datetime.time(self.nzhour, self.nzmin, self.nzsec, self.nzmsec * 1000)
        return _kztime.isoformat(timespec='milliseconds')
