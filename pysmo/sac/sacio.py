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
Python module for reading/writing SAC files using the :class:`SacFile` class.
"""

from __future__ import absolute_import, division, print_function
from builtins import (str, open, zip, object)
from sys import byteorder
import struct
from .sacheader import SacHeader, header_fields

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""


class SacFile(object):
    """
    Python class for accessing SAC files. This class reads and writes directly to a SAC file,
    meaning that any changes to an instance of this module are also immediately written
    to the SAC file. 

    The :class:SacFile class focuses only on reading/writing data and header values to and 
    from a SAC file. Usage is therefore also quite simple, as shown in the examples below.

    Reading and print data::

        >>> from pysmo.sac.sacio import SacFile
        >>> my_sac = SacFile('file.sac', 'rw')
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

    There are a lot of header fields in a SAC file, which are all called the same way when using :class:`Sacfile`.
    They are all listed below.
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

    def __init__(self, filename, mode='ro', **kwargs):
        """
        Open the SAC file with mode read "ro", write "rw" or new "new".
        """
        if mode not in ('ro', 'rw', 'new'):
            raise ValueError('mode=%s not in (ro, rw, new)' % mode)
        else:
            self.mode = mode
            self.filename = filename

        if mode == 'ro':
            self.fh = open(filename, 'rb')
        elif mode == 'rw':
            self.fh = open(filename, 'r+b')
            if self._file_byteorder != self._machine_byteorder:
                self.__convert_file_byteorder()
        elif mode == 'new':
            self.fh = open(filename, 'w+b')
            self.__setupnew()

        for name, value in kwargs.items():
            setattr(self, name, value)

    def __convert_file_byteorder(self):
        """
        Change the file byte order to the system byte order.
        This works (or should work), because we read the file
        in the detected file byteorder, and automatically
        write in machine byteorder.
        """
        # read data in old byteorder first and save it
        tmpdata = self.data

        # switch byteorder for all headervariables except for
        # unused12, which we use for detecting endianness
        for header_field in header_fields.keys():
            if header_field == 'unused12':
                continue
            try:
                header_value = getattr(self, header_field)
            except ValueError:
                header_value = SacHeader.header_undefined_value(header_field)
            setattr(self, header_field, header_value)
        # With all other headers change to native byteorder, we change
        # change unused12 before writing back data
        self.unused12 = SacHeader.header_undefined_value('unused12')
        self.data = tmpdata

    def __del__(self):
        self.fh.close()

    def close(self):
        """
        Close file.
        """
        self.__del__()

    @property
    def _file_byteorder(self):
        """
        Check the byte order of a SAC file
        """
        self.fh.seek(276) # this is where unused12 is located

        # try reading with little endianness
        if struct.unpack('<f', (self.fh.read(4)))[-1] == -12345.0:
            return '<'
        # guess we weren't able to read that, so we assume big endianness.
        return '>'

    @property
    def _machine_byteorder(self):
        """
        Return machine byteorder to use with pack/unpack.
        """
        if byteorder == 'little':
            return '<'
        return '>'

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
        """
        start1 = 632
        length = self.npts * 4
        data_format = self._file_byteorder + str(self.npts) + 'f'
        self.fh.seek(start1)
        data1 = struct.unpack(data_format, self.fh.read(length))
        try:
            data2 = struct.unpack(data_format, self.fh.read(length))
            data = []
            for x1, x2 in zip(data1, data2):
                data.append((x1, x2))
                return data
        except:
            return list(data1)

    @data.setter
    def data(self, data):
        if self.mode == 'ro':
            raise IOError('File %s is readonly' % self.filename)
        self.npts = len(data)
        start1 = 632
        # do we need to write 1 or 2 data sections?
        if isinstance(data[0], tuple):
            dimesions = 2
        else:
            dimensions = 1
        data1 = []
        data2 = []
        for x in data:
            if dimensions == 1:
                data1.append(x)
            elif dimensions == 2:
                data1.append(x[0])
                data2.append(x[1])
        data1.extend(data2)
        self.fh.truncate(start1)
        self.fh.seek(start1)
        for x in data1:
            self.fh.write(struct.pack('f', x))
        self.__sanitycheck()

    def __setupnew(self):
        """
        Setup new file and set required header fields to sane values.
        """
        for header_field in header_fields.keys():
            header_value = SacHeader.header_undefined_value(header_field)
            setattr(self, header_field, header_value)
        self.npts = 0
        self.nvhdr = 6
        self.b = 0
        self.e = 0
        self.iftype = 'time'
        self.leven = 1
        self.delta = 1

    def __sanitycheck(self):
        """
        Calculate and set header fields that describe the data.
        """
        self.e = self.b + (self.npts - 1) * self.delta
        self.depmin = min(self.data)
        self.depmax = max(self.data)
        self.depmen = sum(self.data)/self.npts

# Set this for compatibility
sacfile = SacFile
