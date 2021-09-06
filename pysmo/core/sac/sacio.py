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

"""
Python module for reading/writing SAC files using the :class:`SacIO` class.
"""

__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"

import struct
import datetime
import io
import requests
import urllib.parse
import zipfile
from .sacheader import (SacAlphanumericHeader, SacAuxHeader, SacEnumeratedHeader, SacFloatHeader,
                        SacIntHeader, SacLogicalHeader, HEADER_FIELDS)


class SacIO:
    """
    The :class:`SacIO` class reads and writes data and header values to and from a
    SAC file. Instances of :class:`SacIO` provide attributes named identially to
    header names in the SAC file format. Additonal attributes may be set, but are
    not written to a SAC file (because there is no space reserved for them there).
    Class attributes with corresponding header fields in a SAC file (for example the
    begin time `b`) are checked for a valid format before being saved in the
    :class:`SacIO` instance.


    Read and print data::

        >>> from pysmo import SacIO
        >>> my_sac = SacIO.from_file('file.sac')
        >>> data = my_sac.data
        >>> data
        [-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, ...

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

        >>> from pysmo import SacIO
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

    There are a lot of header fields in a SAC file, which are all called the
    same way when using :class:`SacIO`. They are all listed below.
    """

    # Dynamicall create Descriptors for all header fields
    for header_name in HEADER_FIELDS.keys():
        if HEADER_FIELDS[header_name]['header_type'] == 'f':
            locals()[header_name] = SacFloatHeader()
        elif HEADER_FIELDS[header_name]['header_type'] == 'n':
            locals()[header_name] = SacIntHeader()
        elif HEADER_FIELDS[header_name]['header_type'] == 'i':
            locals()[header_name] = SacEnumeratedHeader()
        elif HEADER_FIELDS[header_name]['header_type'] == 'l':
            locals()[header_name] = SacLogicalHeader()
        elif HEADER_FIELDS[header_name]['header_type'] == 'k':
            locals()[header_name] = SacAlphanumericHeader()
        elif HEADER_FIELDS[header_name]['header_type'] == 'a':
            locals()[header_name] = SacAuxHeader()
        else:
            raise RuntimeError(f"Unable to create header field for {header_name}")

    def __init__(self, **kwargs):
        """
        Initialise a SAC object.
        """
        # set all header fields to None to populate the private_name with the SAC unknown values:
        for header_name in HEADER_FIELDS.keys():
            setattr(self, header_name, None)

        # Set some sane defaults
        self._nvhdr = 6
        self._npts = 0
        self._delta = 1
        self._b = 0
        self.data = []

        for name, value in kwargs.items():
            setattr(self, name, value)

    def read(self, filename):
        """
        Read data and header values from a SAC file into an
        existing SacIO instance.
        """

        with open(filename, 'rb') as file_handle:
            self.read_buffer(file_handle.read())

    def read_buffer(self, buffer):
        """
        Read data and header values from a SAC byte buffer into an
        existing SacIO instance.
        """

        if len(buffer) < 632:
            raise EOFError()

        # Guess the file endianness first using the unused12 header field.
        # It is located at position 276 and it's value should be -12345.0.

        # try reading with little endianness
        if struct.unpack('<f', buffer[276:280])[-1] == -12345.0:
            file_byteorder = '<'
        # otherwise assume big endianness.
        else:
            file_byteorder = '>'

        # Loop over all header fields and store them in the SAC object.
        for header_field in HEADER_FIELDS.keys():
            header_properties = getattr(type(self), header_field)
            private_name = header_properties.private_name
            start = header_properties.sac_start_position
            end = start + header_properties.sac_length
            if end >= len(buffer):
                continue
            content = buffer[start:end]
            value = struct.unpack(file_byteorder + header_properties.sac_format, content)[0]
            if isinstance(value, bytes):
                value = value.decode().rstrip()
            setattr(self, private_name, value)

        # Read first data block
        start1 = 632
        length = self.npts * 4
        end1 = start1 + length
        data_format = file_byteorder + str(self.npts) + 'f'
        if end1 > len(buffer):
            raise EOFError()

        content = buffer[start1:end1]
        data1 = struct.unpack(data_format, content)

        # Try reading second data block and combine both blocks
        # to a list of tuples. If it fails return only the first
        # data block as a list.
        # NOTE: I've never encountered such a file in
        # the wild, and this is somewhat untested...
        try:
            content = buffer[start1+length:end1+length]
            data2 = struct.unpack(data_format, content)
            data = []
            for x1, x2 in zip(data1, data2):
                data.append((x1, x2))
            self._data = data
        except Exception:
            self._data = list(data1)
            if self.depmen is None:
                self._depmen = sum(data1)/self.npts

        if self.depmin is None:
            self._depmin = min(data1)

        if self.depmax is None:
            self._depmax = max(data1)

    @classmethod
    def from_file(cls, filename):
        """
        Create a new SacIO instance from a SAC file.
        """
        newinstance = SacIO()
        newinstance.read(filename)
        return newinstance

    @classmethod
    def from_buffer(cls, buffer):
        """
        Create a new SacIO instance from a SAC data buffer.
        """
        newinstance = SacIO()
        newinstance.read_buffer(buffer)
        return newinstance

    @classmethod
    def from_iris(cls, net, sta, cha, loc, force_single_result=False, **kwargs):
        """
        Create a list of SacIO instances from a single IRIS
        request using the output format as "sac.zip".

        :param force_single_result: If true, the function will return
                                    a single SacIO object or None if
                                    the requests returns nothing.
        :type force_single_result: bool
        """
        kwargs["net"] = net
        kwargs["sta"] = sta
        kwargs["cha"] = cha
        kwargs["loc"] = loc
        kwargs["output"] = "sac.zip"

        if type(kwargs["start"]) == datetime.datetime:
            kwargs["start"] = kwargs["start"].isoformat()

        end = kwargs.get("end", None)
        if end is not None and type(end) == datetime.datetime:
            kwargs["end"] = end.isoformat()

        base = "https://service.iris.edu/irisws/timeseries/1/query"
        params = urllib.parse.urlencode(kwargs, doseq=False)
        url = f"{base}?{params}"
        response = requests.get(url)
        zip = zipfile.ZipFile(io.BytesIO(response.content))
        result = {}
        for name in zip.namelist():
            buffer = zip.read(name)
            sac = SacIO.from_buffer(buffer)
            if force_single_result:
                return sac
            result[name] = sac
        return None if force_single_result else result

    def write(self, filename):
        """
        Write data and header values to a SAC file
        """
        with open(filename, 'wb') as file_handle:
            # loop over all valid header fields and write them to the file
            for header_field in HEADER_FIELDS:
                header_properties = getattr(type(self), header_field)
                file_handle.seek(header_properties.sac_start_position)
                private_value = getattr(self, header_properties.private_name)
                if isinstance(private_value, str):
                    private_value = private_value.encode()
                private_value = struct.pack(header_properties.sac_format, private_value)
                file_handle.write(private_value)

            # write data (if npts > 0)
            if self.npts > 0:
                start1 = 632
                file_handle.truncate(start1)
                file_handle.seek(start1)

                data = self._data

                # do we need to write 1 or 2 data sections?
                if isinstance(data[0], tuple):
                    data1 = []
                    data2 = []
                    for x in data:
                        data1.append(x[0])
                        data2.append(x[1])
                        data1.extend(data2)
                else:
                    data1 = data
                for x in data1:
                    file_handle.write(struct.pack('f', x))

    @property
    def data(self):
        """
        First data section:
            - dependent variable
            - amplitude
            - real component
        Second data section (if it exists):
            - independent variable unevenly spaced
            - phase
            - imaginary component

        If there is only one data section, it is returned as a list of floats.
        Two data sections result in returning a list of tuples.
        """
        return self._data

    @data.setter
    def data(self, data):
        """
        Set the data and additionally write it to
        a SAC file if there is an open filehandle.
        """

        # Data is stored as _data inside the object
        self._data = data

        # Calculate number of points from the length of the data vector
        self._npts = len(data)

        # This triggers recalculating end time
        self.b = self.b
        # Determine if data has one or two data sections
        # and calculate trace stats
        if self.npts > 0:
            if isinstance(data[0], tuple):
                self._depmin = min(data)[0]
                self._depmax = max(data)[0]
                # TODO: Can we do more here than just set it as undefined?
                self.depmen = None
            else:
                self._depmin = min(data)
                self._depmax = max(data)
                self._depmen = sum(data)/self.npts
        else:
            # If npts == 0 these attributes make no sense and are therefore reset
            # to the SAC 'unknown' value by setting the public_name to None
            self.depmin = None
            self.depmax = None
            self.depmen = None

    @property
    def kzdate(self):
        """
        ISO 8601 format of GMT reference date.
        """
        _kzdate = datetime.date(self.nzyear, 1, 1) +\
            datetime.timedelta(self.nzjday)
        return _kzdate.isoformat()

    @property
    def kztime(self):
        """
        Alphanumeric form of GMT reference time.
        """
        _kztime = datetime.time(self.nzhour, self.nzmin, self.nzsec, self.nzmsec * 1000)
        return _kztime.isoformat(timespec='milliseconds')
