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
Python module for reading/writing SAC files.
"""

from sys import byteorder
import struct
import os
import yaml

__copyright__ = """
Copyright (c) 2012 Simon Lloyd
"""

###
# Load SAC header definitions from yaml file and store them in dicts
###
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _header_defs = yaml.load(stream)
_header_types = _header_defs.pop('header_types')
_header_fields = _header_defs.pop('header_fields')
_enumerated_header_values = _header_defs.pop('enumerated_header_values')
# reverse dictionary to look up enumerated strings from ID
_enumerated_header_ids = {v: k for k, v in _enumerated_header_values.items()}


###
# some lambdas and functions for increased readability further down
###
_get_header_start = lambda header_field: _header_fields[header_field]['start']
_get_header_type = lambda header_field: _header_fields[header_field]['header_type']
_get_enum_id = lambda header_value: _enumerated_header_values[header_value]
_valid_enum_values = lambda header_field: _header_fields[header_field]['allowed_vals'].keys()
_get_enumerated_str = lambda header_value: _enumerated_header_ids[header_value]
_get_header_undefined = lambda header_field: _header_types[_get_header_type(header_field)]['undefined']
_is_enumerated_field = lambda header_field: bool('allowed_vals' in _header_fields[header_field])

def _get_header_length(header_field):
    """
    Return header length of a given field.
    """
    try:
        return _header_fields[header_field]['length']
    except KeyError:
        header_type = _get_header_type(header_field)
        return _header_types[header_type]['length']

def _get_header_format(header_field):
    """
    Return header format of a given field. This is
    used to read and write encoded values from the
    binary file.
    """
    try:
        return _header_fields[header_field]['format']
    except KeyError:
        header_type = _get_header_type(header_field)
        return _header_types[header_type]['format']



class sacfile(object):
    """
    Python class for accessing SAC files. Set or read headerfields
    or data.

    Example:
    >>> from pysmo.sac.sacio import sacfile
    >>> sacobj = sacfile('file.sac', 'rw')
    >>> print sacobj.delta
    0.5
    >>> sacobj.delta = 2
    >>> print sacobj.delta
    2
    """

    # Extra attributes besides SAC headers and data
    _attributes = ['fh', 'mode', 'filename', '_file_byteorder', '_machine_byteorder']

    def __init__(self, filename, mode='ro', **kwargs):
        """
        Open the SAC file with mode read "ro", write "rw" or new "new".
        """
        if mode not in ('ro', 'rw', 'new'):
            raise ValueError('mode=%s not in (ro, rw, new)' % mode)
        else:
            setattr(self, 'mode', mode)
            setattr(self, 'filename', filename)
            self.__get_machine_byteorder()

        if mode == 'ro':
            setattr(self, 'fh', open(filename, 'rb'))
            self.__get_file_byteorder()
        elif mode == 'rw':
            f = open(filename, 'r+b')
            setattr(self, 'fh', f)
            self.__get_file_byteorder()
            if self._file_byteorder != self._machine_byteorder:
                self.__convert_file_byteorder()
            self._file_byteorder = self._machine_byteorder
        elif mode == 'new':
            setattr(self, 'fh', open(filename, 'w+b'))
            self._file_byteorder = self._machine_byteorder
            self.__setupnew()
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __get_file_byteorder(self):
        """
        Check the byte order of a SAC file and store it in self._file_byteorder.
        """
        # seek position of 'unused12', which should be -12345.0
        self.fh.seek(276)
        if struct.unpack('>f', (self.fh.read(4)))[-1] == -12345.0:
            self._file_byteorder = '>'
        else:
            self._file_byteorder = '<'

    def __convert_file_byteorder(self):
        """
        Change the file byte order to the system byte order.
        This works (or should work), because we read the file
        in the detected file byteorder, and automatically
        write in machine byteorder.
        """
        # read the data first and save it
        try:
            data = self.__readdata(3)
        except:
            try:
                data = self.__readdata(2)
            except:
                data = self.__readdata(1)
        # switch byteorder for all headervariables
        for header_field in _header_fields.keys():
            try:
                header_value = self.__readhead(header_field)
            except ValueError:
                header_value = _get_header_undefined(header_field)
            self.__writehead(header_field, header_value)
        self.__get_file_byteorder()
        try:
            self.__writedata(data, 3)
        except:
            try:
                self.__writedata(data, 2)
            except:
                self.__writedata(data, 1)

    def __get_machine_byteorder(self):
        """
        Check the system byte order and store it in self._machine_byteorder.
        """
        if byteorder == 'little':
            self._machine_byteorder = '<'
        else:
            self._machine_byteorder = '>'

    def __del__(self):
        self.fh.close()

    def close(self):
        """
        Close file.
        """
        self.__del__()

    def __getattr__(self, name):
        if name in _header_fields.keys():
            return self.__readhead(name)
        elif name == 'data':
            return self.__readdata(1)
        elif name == 'data2D':
            return self.__readdata(2)
        elif name == 'data3D':
            return self.__readdata(3)
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in _header_fields.keys():
            self.__writehead(name, value)
        elif name == 'data':
            self.__writedata(value, 1)
            self.__sanitycheck()
        elif name == 'data2D':
            self.__writedata(value, 2)
        elif name == 'data3D':
            self.__writedata(value, 3)
        elif name in self._attributes:
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(name)

    def __readhead(self, header_field):
        """
        Read header field from SAC file. Enumerated
        header fields are automatically translated.
        """
        header_start = _get_header_start(header_field)
        header_length = _get_header_length(header_field)
        header_format = _get_header_format(header_field)
        header_type = _get_header_type(header_field)
        header_undefined = _header_types[header_type]['undefined']
        self.fh.seek(header_start)
        content = self.fh.read(header_length)
        header_value = struct.unpack(self._file_byteorder+header_format, content)[0]
        if isinstance(header_value, bytes):
            header_value = header_value.decode().rstrip()
        if header_value == header_undefined:
            raise ValueError('Header %s is undefined' % header_field)
        if _is_enumerated_field(header_field):
            return _get_enumerated_str(header_value)
        return header_value

    def __writehead(self, header_field, header_value):
        """
        Write header field to SAC file. Enumerated
        header fields are automatically translated.
        """
        if self.mode == 'ro':
            raise IOError('File %s is readonly' % self.filename)
        header_start = _get_header_start(header_field)
        header_format = _get_header_format(header_field)
        header_undefined = _get_header_undefined(header_field)
        if _is_enumerated_field(header_field) and header_value != header_undefined:
            if header_value in _valid_enum_values(header_field):
                header_value = _get_enum_id(header_value)
            else:
                raise ValueError('%s not an allowed value for %s' % \
                (header_value, header_field))
        try:
            # python2
            if isinstance(header_value, unicode):
                header_value = header_value.encode()
        except NameError:
            # python3 str type represents unicode strings
            if isinstance(header_value, str):
                header_value = header_value.encode()
        header_value = struct.pack(header_format, header_value)
        self.fh.seek(header_start)
        self.fh.write(header_value)

    def __readdata(self, dimensions):
        """
        Read 1D, 2D or 3D data from SAC file.
        """
        data = []
        data_format = self._file_byteorder + str(self.npts) + 'f'
        length = self.npts * 4
        self.fh.seek(632)
        content = self.fh.read(length)
        sacdata1 = struct.unpack(data_format, content)
        if dimensions >= 2:
            content = self.fh.read(length)
            sacdata2 = struct.unpack(data_format, content)
        if dimensions == 3:
            content = self.fh.read(length)
            sacdata3 = struct.unpack(data_format, content)
        if dimensions == 1:
            for x1 in sacdata1:
                data.append(x1)
        elif dimensions == 2:
            for x1, x2 in zip(sacdata1, sacdata2):
                data.append((x1, x2))
        elif dimensions == 3:
            for x1, x2, x3 in zip(sacdata1, sacdata2, sacdata3):
                data.append((x1, x2, x3))
        return data

    def __writedata(self, data, dimensions,):
        """
        Write 1D, 2D or 3D data to SAC file.
        """
        if self.mode == 'ro':
            raise IOError('File %s is readonly' % self.filename)
        self.__writehead('npts', len(data))
        self.fh.truncate(632)
        self.fh.seek(632)
        data1 = []
        data2 = []
        data3 = []
        for x in data:
            if dimensions == 1:
                data1.append(x)
            elif dimensions >= 2:
                data1.append(x[0])
                data2.append(x[1])
            if dimensions == 3:
                data3.append(x[2])
        data1.extend(data2)
        data1.extend(data3)
        for x in data1:
            self.fh.write(struct.pack('f', x))

    def __setupnew(self):
        """
        Setup new file and set required header fields to sane values.
        """
        for header_field in _header_fields.keys():
            header_undefined = _get_header_undefined(header_field)
            self.__writehead(header_field, header_undefined)
        self.__writehead('npts', 0)
        self.__writehead('nvhdr', 6)
        self.__writehead('b', 0)
        self.__writehead('e', 0)
        self.__writehead('iftype', 'time')
        self.__writehead('leven', 1)
        self.__writehead('delta', 1)

    def __sanitycheck(self):
        """
        Calculate and set header fields that describe the data.
        """
        self.__writehead('e', self.b + (self.npts - 1) * self.delta)
        self.__writehead('depmin', min(self.data))
        self.__writehead('depmax', max(self.data))
        self.__writehead('depmen', sum(self.data)/self.npts)
