###
# This file is part of pysmo.

# psymo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
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

from __future__ import absolute_import, division, print_function
from builtins import (str, open, zip, object)
import struct
from contextlib import contextmanager
from .sacheader import SacHeader, _HEADER_FIELDS

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""


class SacIO(object):
    """
    The :class:`SacIO` class reads and writes data and header values to and from a SAC file.
    Additonal class attributes may be set, but are not written to a SAC file (because
    there is no space reserved for them there). Class attributes with corresponding header
    fields in a SAC file (for example the begin time `b`) are checked for a valid format
    before being saved in the :class:`SacIO` instance.


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

    There are a lot of header fields in a SAC file, which are all called the same way
    when using :class:`SacIO`. They are all listed below.
    """

    # Descriptors for all header fields
    delta = SacHeader("delta")
    depmin = SacHeader("depmin")
    depmax = SacHeader("depmax")
    scale = SacHeader("scale")
    odelta = SacHeader("odelta")
    b = SacHeader("b")
    e = SacHeader("e")
    o = SacHeader("o")
    a = SacHeader("a")
    fmt = SacHeader("fmt")
    t0 = SacHeader("t0")
    t1 = SacHeader("t1")
    t2 = SacHeader("t2")
    t3 = SacHeader("t3")
    t4 = SacHeader("t4")
    t5 = SacHeader("t5")
    t6 = SacHeader("t6")
    t7 = SacHeader("t7")
    t8 = SacHeader("t8")
    t9 = SacHeader("t9")
    f = SacHeader("f")
    resp0 = SacHeader("resp0")
    resp1 = SacHeader("resp1")
    resp2 = SacHeader("resp2")
    resp3 = SacHeader("resp3")
    resp4 = SacHeader("resp4")
    resp5 = SacHeader("resp5")
    resp6 = SacHeader("resp6")
    resp7 = SacHeader("resp7")
    resp8 = SacHeader("resp8")
    resp9 = SacHeader("resp9")
    stla = SacHeader("stla")
    stlo = SacHeader("stlo")
    stel = SacHeader("stel")
    stdp = SacHeader("stdp")
    evla = SacHeader("evla")
    evlo = SacHeader("evlo")
    evel = SacHeader("evel")
    evdp = SacHeader("evdp")
    mag = SacHeader("mag")
    user0 = SacHeader("user0")
    user1 = SacHeader("user1")
    user2 = SacHeader("user2")
    user3 = SacHeader("user3")
    user4 = SacHeader("user4")
    user5 = SacHeader("user5")
    user6 = SacHeader("user6")
    user7 = SacHeader("user7")
    user8 = SacHeader("user8")
    user9 = SacHeader("user9")
    dist = SacHeader("dist")
    az = SacHeader("az")
    baz = SacHeader("baz")
    gcarc = SacHeader("gcarc")
    sb = SacHeader("sb")
    sdelta = SacHeader("sdelta")
    depmen = SacHeader("depmen")
    cmpaz = SacHeader("cmpaz")
    cmpinc = SacHeader("cmpinc")
    xminimum = SacHeader("xminimum")
    xmaximum = SacHeader("xmaximum")
    yminimum = SacHeader("yminimum")
    ymaximum = SacHeader("ymaximum")
    unused6 = SacHeader("unused6")
    unused7 = SacHeader("unused7")
    unused8 = SacHeader("unused8")
    unused9 = SacHeader("unused9")
    unused10 = SacHeader("unused10")
    unused11 = SacHeader("unused11")
    unused12 = SacHeader("unused12")
    nzyear = SacHeader("nzyear")
    nzjday = SacHeader("nzjday")
    nzhour = SacHeader("nzhour")
    nzmin = SacHeader("nzmin")
    nzsec = SacHeader("nzsec")
    nzmsec = SacHeader("nzmsec")
    nvhdr = SacHeader("nvhdr")
    norid = SacHeader("norid")
    nevid = SacHeader("nevid")
    npts = SacHeader("npts")
    nsnpts = SacHeader("nsnpts")
    nwfid = SacHeader("nwfid")
    nxsize = SacHeader("nxsize")
    nysize = SacHeader("nysize")
    unused15 = SacHeader("unused15")
    iftype = SacHeader("iftype")
    idep = SacHeader("idep")
    iztype = SacHeader("iztype")
    unused16 = SacHeader("unused16")
    iinst = SacHeader("iinst")
    istreg = SacHeader("istreg")
    ievreg = SacHeader("ievreg")
    ievtyp = SacHeader("ievtyp")
    iqual = SacHeader("iqual")
    isynth = SacHeader("isynth")
    imagtyp = SacHeader("imagtyp")
    imagsrc = SacHeader("imagsrc")
    unused19 = SacHeader("unused19")
    unused20 = SacHeader("unused20")
    unused21 = SacHeader("unused21")
    unused22 = SacHeader("unused22")
    unused23 = SacHeader("unused23")
    unused24 = SacHeader("unused24")
    unused25 = SacHeader("unused25")
    unused26 = SacHeader("unused26")
    leven = SacHeader("leven")
    lpspol = SacHeader("lpspol")
    lovrok = SacHeader("lovrok")
    lcalda = SacHeader("lcalda")
    unused27 = SacHeader("unused27")
    kstnm = SacHeader("kstnm")
    kevnm = SacHeader("kevnm")
    khole = SacHeader("khole")
    ko = SacHeader("ko")
    ka = SacHeader("ka")
    kt0 = SacHeader("kt0")
    kt1 = SacHeader("kt1")
    kt2 = SacHeader("kt2")
    kt3 = SacHeader("kt3")
    kt4 = SacHeader("kt4")
    kt5 = SacHeader("kt5")
    kt6 = SacHeader("kt6")
    kt7 = SacHeader("kt7")
    kt8 = SacHeader("kt8")
    kt9 = SacHeader("kt9")
    kf = SacHeader("kf")
    kuser0 = SacHeader("kuser0")
    kuser1 = SacHeader("kuser1")
    kuser2 = SacHeader("kuser2")
    kcmpnm = SacHeader("kcmpnm")
    knetwk = SacHeader("knetwk")
    kdatrd = SacHeader("kdatrd")
    kinst = SacHeader("kinst")

    def __init__(self, **kwargs):
        """
        Initialise a SAC object.
        """

        self._data = []
        self.force = False
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __getstate__(self):
        return_dict = self.__dict__.copy()
        for header_field in _HEADER_FIELDS:
            return_dict[header_field] = getattr(self, header_field)
        return return_dict

    def __setstate__(self, d):
        with self.force_set_header():
            for header_field in _HEADER_FIELDS:
                setattr(self, header_field, d.pop(header_field))
        self.__dict__ = d

    @contextmanager
    def force_set_header(self):
        """
        This provides a context to force setting otherwise unsettable
        sac header fields (e.g. npts, which is usually determined from
        the length of the data vector)
        """
        self.force = True
        yield
        self.force = False

    def read(self, filename):
        """
        Read data and header values from a SAC file into an
        existing SacIO instance.
        """

        with open(filename, 'rb') as file_handle:

            # Guess the file endianness first using the unused12 header field.
            # It's value should be -12345.0

            # This is where unused12 is located
            file_handle.seek(276)

            # try reading with little endianness
            if struct.unpack('<f', (file_handle.read(4)))[-1] == -12345.0:
                file_byteorder = '<'
            # otherwise assume big endianness.
            else:
                file_byteorder = '>'

            # Loop over all header fields and store them in the SAC object.
            with self.force_set_header():
                for header_field in _HEADER_FIELDS:
                    desc = getattr(type(self), header_field)
                    file_handle.seek(desc.start)
                    content = file_handle.read(desc.length)
                    value = struct.unpack(file_byteorder+desc.format, content)[0]
                    if isinstance(value, bytes):
                        value = value.decode().rstrip()
                    setattr(self, header_field, value)


            # Read first data block
            start1 = 632
            length = self.npts * 4
            data_format = file_byteorder + str(self.npts) + 'f'
            file_handle.seek(start1)
            data1 = struct.unpack(data_format, file_handle.read(length))

            # Try reading second data block and combine both blocks
            # to a list of tuples. If it fails return only the first
            # data block as a list
            try:
                data2 = struct.unpack(data_format, file_handle.read(length))
                data = []
                for x1, x2 in zip(data1, data2):
                    data.append((x1, x2))
                self._data = data
            except:
                self._data = list(data1)

    @classmethod
    def from_file(cls, filename):
        """
        Create a new SacIO instance from a SAC file.
        """
        newinstance = SacIO()
        newinstance.read(filename)
        return newinstance

    def write(self, filename):
        """
        Write data and header values to a SAC file
        """
        with open(filename, 'wb') as file_handle:
            # loop over all valid header fields and write them to the file
            for header_field in _HEADER_FIELDS:
                desc = getattr(type(self), header_field)
                file_handle.seek(desc.start)
                value = getattr(self, header_field)
                if value is None:
                    value = desc.undefined

                # convert enumerated headers to corresponding string
                if desc.is_enumerated:
                    try:
                        value = SacHeader.enumerated_str2int(value)
                    except KeyError:
                        value = desc.undefined

                if isinstance(value, str):
                    value = value.encode()
                value = struct.pack(desc.format, value)
                file_handle.write(value)


            # write data
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

        # Update header values that depend on the
        # data. The tuple is used to allow setting
        # of quasi-immutable header values (i.e. ones
        # that depend on the data)

        # This triggers recalculating end time
        self.b = self.b

        with self.force_set_header():
            # Calculate number of points from the length of the data vector
            self.npts = len(data)
            # Determine if data has one or two data sections
            # and calculate trace stats
            if isinstance(data[0], tuple):
                self.depmin = min(data)[0]
                self.depmax = max(data)[0]
                # TODO: Can we do more here than just set it as undefined?
                self.depmen = None
            else:
                self.depmin = min(data)
                self.depmax = max(data)
                self.depmen = sum(data)/self.npts
