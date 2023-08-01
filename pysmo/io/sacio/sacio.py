###
# This file is part of pysmo.

# psymo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# psymo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pysmo.  If not, see <http://www.gnu.org/licenses/>.
###
from __future__ import annotations

__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"

import struct
import datetime
import io
import requests
import urllib.parse
import zipfile
import warnings
import numpy as np
from typing import Union, Optional, Any
from typing_extensions import Self
from .sacheader import HEADER_FIELDS, SacHeaderFactory


class _SacMeta(type):
    """Metaclass that adds the SacHeader descriptors to the class."""

    def __new__(cls, name, bases, dct):  # type: ignore
        for header_name in HEADER_FIELDS:
            header_class = SacHeaderFactory(header_name)
            dct[header_name] = header_class()
        return super().__new__(cls, name, bases, dct)


class _SacIO(metaclass=_SacMeta):
    """
    The :class:`_SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of :class:`_SacIO` provide attributes named identially to
    header names in the SAC file format. Additonal attributes may be set, but are
    not written to a SAC file (because there is no space reserved for them there).
    Class attributes with corresponding header fields in a SAC file (for example the
    begin time `b`) are checked for a valid format before being saved in the
    :class:`_SacIO` instance.


    Read and print data::

        >>> from pysmo import SAC
        >>> my_sac = SAC.from_file('file.sac')
        >>> data = my_sac.data
        >>> data
        array([-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, ...

    Read the sampling rate::

        >>> delta = my_sac.delta
        >>> delta
        0.019999999552965164

    Change the sampling rate::

        >>> newdelta = 0.05
        >>> my_sac.delta = newdelta
        >>> my_sac.delta
        0.05

    Read from IRIS services::

        >>> from pysmo import SAC
        >>> my_sac = SAC.from_iris(
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
    same way when using :class:`SAC`. They are all listed below.
    """
    # type annotations:
    # f -> float
    delta: float
    depmin: Union[float, None]
    depmax: Union[float, None]
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
    depmen: Union[float, None]
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
        """Initialises a SAC object."""
        # All SAC header fields have a private and a public name. For example the sample rate has a
        # public name of delta, and a private name of _delta. Here, delta is a descriptor that takes
        # care of converting from a SAC file to python (formatting, enumerated headers etc), and
        # _delta is the SAC formatted value stored as a normal attribute. In other words, reading
        # and writing SAC files uses _delta, whereas accessing the header within Python uses delta.

        # The descriptor converts None to the SAC unknown value (e.g. -12345 for int type header fields).
        # Therefore this loop sets the initial value for all private fields to the SAC unknown value.
        for header_name in HEADER_FIELDS:
            setattr(self, header_name, None)

        # Set some sane defaults
        #
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

        # Set whatever other kwargs were provided at instance creation
        for name, value in kwargs.items():
            setattr(self, name, value)

    def read(self, filename: str) -> None:
        """Read data and header values from a SAC file into an existing SAC instance."""

        with open(filename, 'rb') as file_handle:
            self.read_buffer(file_handle.read())

    def read_buffer(self, buffer: bytes) -> None:
        """Read data and header values from a SAC byte buffer into an existing SAC instance."""

        if len(buffer) < 632:
            raise EOFError()

        # Guess the file endianness first using the unused12 header field.
        # It is located at position 276 and it's value should be -12345.0.
        # Try reading with little endianness
        if struct.unpack('<f', buffer[276:280])[-1] == -12345.0:
            file_byteorder = '<'
        # otherwise assume big endianness.
        else:
            file_byteorder = '>'

        # Loop over all header fields and store them in the SAC object under their
        # respective private names.
        for header_field in HEADER_FIELDS:
            header_class = getattr(type(self), header_field)
            end = header_class.sac_start_position + header_class.sac_length
            if end >= len(buffer):
                continue
            content = buffer[header_class.sac_start_position:end]
            value = struct.unpack(file_byteorder + header_class.sac_format, content)[0]
            if isinstance(value, bytes):
                value = value.decode().rstrip()
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
        """
        Creates a new SAC instance from a SAC file.

        :param filename: Name of the file to read.
        """
        newinstance = cls()
        newinstance.read(filename)
        return newinstance

    @classmethod
    def from_buffer(cls, buffer: bytes) -> Self:
        """Create a new SAC instance from a SAC data buffer."""
        newinstance = cls()
        newinstance.read_buffer(buffer)
        return newinstance

    @classmethod
    def from_iris(cls, net: str, sta: str, cha: str, loc: str, force_single_result: bool = False,
                  **kwargs: Any) -> Union[Self, Optional[dict[str, Self]]]:
        """
        Create a list of SAC instances from a single IRIS
        request using the output format as "sac.zip".

        :param force_single_result: If true, the function will return
                                    a single SAC object or None if
                                    the requests returns nothing.
        :type force_single_result: bool
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
        """
        Writes data and header values to a SAC file.

        :param filename: Name of the sacfile to write to.
        """
        with open(filename, 'wb') as file_handle:
            # loop over all valid header fields and write them to the file
            for header_field in HEADER_FIELDS:
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
        """Returns ISO 8601 format of GMT reference date."""
        _kzdate = datetime.date(self.nzyear, 1, 1) + datetime.timedelta(self.nzjday - 1)
        return _kzdate.isoformat()

    @property
    def kztime(self) -> str:
        """Returns alphanumeric form of GMT reference time."""
        _kztime = datetime.time(self.nzhour, self.nzmin, self.nzsec, self.nzmsec * 1000)
        return _kztime.isoformat(timespec='milliseconds')

    @property
    def data(self) -> np.ndarray:
        """Returns seismogram data."""
        return self._data

    @data.setter
    def data(self, value: np.ndarray) -> None:
        """
        Sets the seismogram data. This will also update the end time header
        value 'e' as well as depmin, depmax, and depmen.

        :param data: numpy array containing seismogram data
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
