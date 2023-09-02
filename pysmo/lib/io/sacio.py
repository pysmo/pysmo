from __future__ import annotations
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
from abc import ABC, abstractmethod
from typing import Any, Sized
from typing_extensions import Self


# Read yaml file with dictionaries describing SAC headers
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _HEADER_DEFS: dict = yaml.safe_load(stream)

# Dictionary of header types (default values etc)
_HEADER_TYPES: dict = _HEADER_DEFS.pop('header_types')
# Dictionary of header fields (format, type, etc)
_HEADER_FIELDS: dict = _HEADER_DEFS.pop('header_fields')
# Dictionary of enumerated headers (to convert int to str).
_ENUM_DICT: dict = _HEADER_DEFS.pop('enumerated_header_values')


class SacHeader(ABC):
    """Python descriptor (abstract)class for SAC file headers."""

    def __set_name__(self, owner: SacIO, name: str) -> None:
        self.public_name: str = name
        self.private_name: str = '_' + name
        # Set docstring while we are here too.
        try:
            self.__doc__: str = _HEADER_FIELDS[name]['description']
            try:
                allowed_vals = _HEADER_FIELDS[name]['allowed_vals']
                self.__doc__ += f" ``{name}`` must be one of:\n"
                for val, desc in allowed_vals.items():
                    self.__doc__ += f"\n- {val}:  {desc}"
            except KeyError:
                pass
        except Exception:
            pass

    def __get__(self, obj: SacIO | None, objtype: _SacMeta | None = None) -> Self | float | int | str | bool | None:
        # instance attribute accessed on class, return self
        if obj is None:
            return self

        # The private_value content is in the same format as in a SAC file.
        private_value = getattr(obj, self.private_name)

        # Instead of returning SAC unknown placeholders (e.g. -12345) return
        # the more pythonic 'None'.
        if private_value == self.private_undefined:
            return None

        # Format value before returning. This will also translate enumerated headers.
        return self.format2public(private_value)

    def __set__(self, obj: SacIO, public_value: float | int | str | bool | None) -> None:
        # Setting the public value to None updates the private value to be the 'undefined'
        # value for that header field. Since this only really is used during initialisation
        # of a SAC instance we don't check for read-only header values.
        if public_value is None:
            setattr(obj, self.private_name, self.private_undefined)

        # Format to SAC format and save to private_name
        else:
            # Some headers are calculated from data/other headers, and should not be set.
            if self.public_read_only:
                raise RuntimeError(f"{self.public_name} is a read-only header field.")

            # Set attribute in SAC internal format.
            setattr(obj, self.private_name, self.validate_and_format2private(public_value))

            # Changing b or delta requires recomputing end time e
            if self.public_name in ('b', 'delta'):
                obj._e = obj.b + (obj.npts - 1) * obj.delta  # type: ignore

    @abstractmethod
    def validate_and_format2private(self, public_value: float | int | str | bool) -> float | int | str:
        """First validates a public value, then converts it to the respective private value (i.e. SAC internal)."""
        pass

    @abstractmethod
    def format2public(self, private_value: float | int | str) -> float | int | str | bool:
        """Format a private value (SAC internal format) to a public value format.

        Method takes care of converting between things like enumerated headers
        and SAC internal 'unknown' values (i.e. -12345 becomes None).

        Parameters:
            private_value: SAC header in the file format.

        Returns:
            SAC header formatted for use in Python.
        """
        pass

    @property
    @abstractmethod
    def header_type(self) -> str:
        """
        Returns:
            The SAC header type (k, f, ...).
        """
        pass

    @property
    def sac_start_position(self) -> int:
        """
        Returns:
            The start position in the binary sac file.
        """
        return int(_HEADER_FIELDS[self.public_name]['start'])

    @property
    def sac_length(self) -> int:
        """
        Returns:
            Length to read from SAC file.
        """
        # Some header fields have their own length that is specified in the dictionary.
        try:
            return int(_HEADER_FIELDS[self.public_name]['length'])
        # If there is no such header field specific format use default one for that type.
        except KeyError:
            return int(_HEADER_TYPES[self.header_type]['length'])

    @property
    def sac_format(self) -> str:
        """
        Returns:
            The SAC format used to write headers to a SAC file.
        """
        # Some header fields have their own format that is specified in the dictionary.
        try:
            return _HEADER_FIELDS[self.public_name]['format']
        # If there is no such header field specific format use default one for that type.
        except KeyError:
            return _HEADER_TYPES[self.header_type]['format']

    @property
    def public_read_only(self) -> bool:
        return _HEADER_FIELDS[self.public_name].get('read_only', False)

    @property
    def private_undefined(self) -> float | int | str | bool:
        return _HEADER_TYPES[self.header_type].get('undefined')


class SacFloatHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('f')

    def validate_and_format2private(self, public_value: float | int | str | bool) -> float:
        if not isinstance(public_value, float | int):
            raise TypeError(f"Setting {self.public_name} to {public_value} failed. " +
                            f"Expected float, got {type(public_value)}.")
        if self.public_name in ("evla", "stla") and not 90 >= public_value >= -90:
            raise ValueError(f"Setting {self.public_name} to {public_value} failed. " +
                             "Latitude must be no smaller than -90 and no greater than 90.")
        elif self.public_name in ("evlo", "stlo") and not 180 >= public_value > -180:
            raise ValueError(f"Setting {self.public_name} to {public_value} failed. " +
                             "Longitude must be greater than -180 and no greater than 180.")
        return float(public_value)

    def format2public(self, private_value: float | int | str) -> float:
        return float(private_value)


class SacIntHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('n')

    def validate_and_format2private(self, public_value: float | int | str | bool) -> int:
        if not isinstance(public_value, int):
            raise TypeError(f"trying to set {self.public_name} to {public_value} failed. " +
                            f"Expected int, got {type(public_value)}.")
        return int(public_value)

    def format2public(self, private_value: float | int | str) -> int:
        return int(private_value)


class SacEnumeratedHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('i')

    def validate_and_format2private(self, public_value: float | int | str | bool) -> int:
        # Convert from string to int
        return _ENUM_DICT[public_value]

    def format2public(self, private_value: float | int | str) -> str:
        # convert from int to string
        int2str_dict = {v: k for k, v in _ENUM_DICT.items()}
        return int2str_dict[private_value]


class SacLogicalHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('l')

    def validate_and_format2private(self, public_value: float | int | str | bool) -> bool:
        if not isinstance(public_value, bool):
            raise TypeError(f"trying to set {self.public_name} to {public_value} failed. " +
                            f"Expected bool, got {type(public_value)}.")
        return public_value

    def format2public(self, private_value: float | int | str) -> bool:
        return bool(private_value)


class SacAlphanumericHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('k')

    def validate_and_format2private(self, public_value: Sized | float | int | str | bool) -> str:
        if isinstance(public_value, bool):
            raise TypeError(f"{self.public_name} may not be of type bool")
        if len(str(public_value)) > self.sac_length:
            raise ValueError(f"{public_value} is too long - maximum length for {self.public_name} is {self.sac_length}")
        return str(public_value)

    def format2public(self, private_value: float | int | str) -> str:
        return str(private_value).rstrip()


class SacAuxHeader(SacHeader):

    @property
    def header_type(self) -> str:
        return ('a')

    def validate_and_format2private(self, public_value: Any) -> Any:
        raise RuntimeError(f"I don't know how to format {self.public_name}!")

    def format2public(self, private_value: Any) -> Any:
        raise RuntimeError(f"I don't know how to format {self.public_name}!")


def SacHeaderFactory(header_name: str) -> type[SacHeader]:
    header_map = {
        'f': SacFloatHeader,
        'n': SacIntHeader,
        'i': SacEnumeratedHeader,
        'l': SacLogicalHeader,
        'k': SacAlphanumericHeader,
        'a': SacAuxHeader
    }
    header_type = _HEADER_FIELDS[header_name]['header_type']
    return header_map[header_type]


class _SacMeta(type):
    """Metaclass that adds the SacHeader descriptors to the class."""

    def __new__(cls, name, bases, dct):  # type: ignore
        for header_name in _HEADER_FIELDS:
            header_class = SacHeaderFactory(header_name)
            dct[header_name] = header_class()
        return super().__new__(cls, name, bases, dct)


class SacIO(metaclass=_SacMeta):
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
    # type annotations:
    # f -> float
    delta: float
    depmin: float | None
    depmax: float | None
    scale: float
    odelta: float
    b: float
    e: float
    o: float
    a: float
    fmt: float
    t0: float
    t1: float
    t2: float
    t3: float
    t4: float
    t5: float
    t6: float
    t7: float
    t8: float
    t9: float
    f: float
    resp0: float
    resp1: float
    resp2: float
    resp3: float
    resp4: float
    resp5: float
    resp6: float
    resp7: float
    resp8: float
    resp9: float
    stla: float
    stlo: float
    stel: float
    stdp: float
    evla: float
    evlo: float
    evel: float
    evdp: float
    mag: float
    user0: float
    user1: float
    user2: float
    user3: float
    user4: float
    user5: float
    user6: float
    user7: float
    user8: float
    user9: float
    dist: float
    az: float
    baz: float
    gcarc: float
    sb: float
    sdelta: float
    depmen: float | None
    cmpaz: float
    cmpinc: float
    xminimum: float
    xmaximum: float
    yminimum: float
    ymaximum: float
    unused6: float
    unused7: float
    unused8: float
    unused9: float
    unused10: float
    unused11: float
    unused12: float
    # n --> int
    nzyear: int
    nzjday: int
    nzhour: int
    nzmin: int
    nzsec: int
    nzmsec: int
    nvhdr: int
    norid: int
    nevid: int
    npts: int
    nsnpts: int
    nwfid: int
    nxsize: int
    nysize: int
    unused15: int
    # i (enumerated) -> str
    iftype: str
    idep: str
    iztype: str
    unused16: str
    iinst: str
    istreg: str
    ievreg: str
    ievtyp: str
    iqual: str
    isynth: str
    imagtyp: str
    imagsrc: str
    unused19: str
    unused20: str
    unused21: str
    unused22: str
    unused23: str
    unused24: str
    unused25: str
    unused26: str
    # l (logical) -> bool
    leven: bool
    lpspol: bool
    lovrok: bool
    lcalda: bool
    unused27: bool
    # k (alphanumeric) -> str
    kstnm: str
    kevnm: str
    khole: str
    ko: str
    ka: str
    kt0: str
    kt1: str
    kt2: str
    kt3: str
    kt4: str
    kt5: str
    kt6: str
    kt7: str
    kt8: str
    kt9: str
    kf: str
    kuser0: str
    kuser1: str
    kuser2: str
    kcmpnm: str
    knetwk: str
    kdatrd: str
    kinst: str

    def __init__(self, **kwargs: dict) -> None:
        # All SAC header fields have a private and a public name. For example the sample rate has a
        # public name of delta, and a private name of _delta. Here, delta is a descriptor that takes
        # care of converting from a SAC file to python (formatting, enumerated headers etc), and
        # _delta is the SAC formatted value stored as a normal attribute. In other words, reading
        # and writing SAC files uses _delta, whereas accessing the header within Python uses delta.

        # Set defaults first
        self._set_defaults()

        # Set whatever other kwargs were provided at instance creation
        for name, value in kwargs.items():
            setattr(self, name, value)

    def _set_defaults(self) -> None:
        # The descriptor converts None to the SAC unknown value (e.g. -12345 for int type header fields).
        # Therefore this loop sets the initial value for all private fields to the SAC unknown value.
        for header_name in _HEADER_FIELDS:
            setattr(self, header_name, None)
        # Set some sane defaults:
        # self.npts is read only, so we write to the private name self._ntps directly.
        self._npts = 0
        # Setting self.delta triggers calculation of self.e, but we can't do that without also knowing
        # the begin time self.b - writing to the private self._delta doesn't try to calculate self.e
        self._delta = 1
        # Now we can write to the public self.b, since self.delta is set above. This triggers calculation of self.e
        self.b = 0
        # SAC header version 7 adds a footer after the data block. That is not implemented here.
        self.nvhdr = 6
        self.iftype = "time"
        self.leven = True
        self.data = np.array([])

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

        # Loop over all header fields and store them in the SAC object under their
        # respective private names.
        for header_field in _HEADER_FIELDS:
            header_class = getattr(type(self), header_field)
            end = header_class.sac_start_position + header_class.sac_length
            if end >= len(buffer):
                continue
            content = buffer[header_class.sac_start_position:end]
            value = struct.unpack(file_byteorder + header_class.sac_format, content)[0]
            if isinstance(value, bytes):
                # strip spaces and "\x00" chars
                value = value.decode().rstrip(" \x00")
            setattr(self, header_class.private_name, value)

        # Only accept IFTYPE = ITIME SAC files. Other IFTYPE use two data blocks, which is something
        # we don't support.
        if self.iftype.lower() != 'time':
            raise NotImplementedError(f"Reading SAC files with IFTYPE=(I){self.iftype.upper()} is not supported.")

        # Read first data block
        start = 632
        length = self.npts * 4
        end = start + length
        data_format = file_byteorder + str(self.npts) + 'f'
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
            for header_field in _HEADER_FIELDS:
                header_class = getattr(type(self), header_field)
                file_handle.seek(header_class.sac_start_position)
                private_value = getattr(self, header_class.private_name)
                if isinstance(private_value, str):
                    private_value = private_value.encode()
                private_value = struct.pack(header_class.sac_format, private_value)
                file_handle.write(private_value)

            # write data (if npts > 0)
            if self.npts > 0:
                start1 = 632
                file_handle.truncate(start1)
                file_handle.seek(start1)

                data = self._data

                for x in data:
                    file_handle.write(struct.pack('f', x))

    @property
    def kzdate(self) -> str:
        """
        Returns:
            ISO 8601 format of GMT reference date.
        """
        _kzdate = datetime.date(self.nzyear, 1, 1) + datetime.timedelta(self.nzjday - 1)
        return _kzdate.isoformat()

    @property
    def kztime(self) -> str:
        """
        Returns:
            Alphanumeric form of GMT reference time.
        """
        _kztime = datetime.time(self.nzhour, self.nzmin, self.nzsec, self.nzmsec * 1000)
        return _kztime.isoformat(timespec='milliseconds')

    @property
    def data(self) -> np.ndarray:
        """
        Returns:
            Seismogram data."""
        return self._data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        """Sets the seismogram data. This will also update the end time header
        value 'e' as well as depmin, depmax, and depmen.

        Parameters:
            data: numpy array containing seismogram data
        """
        # Data is stored as _data inside the object
        self._data = value

        # Calculate number of points from the length of the data vector
        self._npts = len(value)

        # This triggers recalculating end time
        self.b = self.b

        # and calculate trace stats
        if self.npts > 0:
            self._depmin = min(self._data)
            self._depmax = max(self._data)
            self._depmen = sum(self._data)/self._npts
        else:
            # If npts == 0 these attributes make no sense and are therefore reset
            # to the SAC 'unknown' value by setting the public_name value to None.
            self.depmin = None
            self.depmax = None
            self.depmen = None
