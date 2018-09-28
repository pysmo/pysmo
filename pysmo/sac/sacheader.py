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

from __future__ import absolute_import, division, print_function
from builtins import (bytes, str, open, object)
import struct
import os
import yaml

__copyright__ = """
Copyright (c) 2018 Simon Lloyd
"""

###
# Load SAC header definitions from yaml file and store them in dicts
###
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _header_defs = yaml.load(stream)
header_types = _header_defs.pop('header_types')
header_fields = _header_defs.pop('header_fields')
enumerated_header_values = _header_defs.pop('enumerated_header_values')
# reverse dictionary to look up enumerated strings from ID
enumerated_header_ids = {v: k for k, v in enumerated_header_values.items()}


class SacHeader(object):
    """
    Python descriptor class for SAC file headers. Mainly for use
    inside the SacFile class.
    """

    def __init__(self, header_field):
        self.name = header_field
        self.start = header_fields[header_field]['start']
        self.header_type = SacHeader.header_type(header_field)
        try:
            self.valid_enum_values = header_fields[header_field]['allowed_vals'].keys()
        except KeyError:
            pass
        self.undefined = header_types[self.header_type]['undefined']
        self.is_enumerated = bool('allowed_vals' in header_fields[header_field])
        if self.is_enumerated:
            self.valid_enum_values = header_fields[header_field]['allowed_vals'].keys()
        try:
            self.format = header_fields[header_field]['format']
        except KeyError:
            self.format = header_types[self.header_type]['format']
        try:
            self.length = header_fields[header_field]['length']
        except KeyError:
            self.length = header_types[self.header_type]['length']
        self.__doc__ = header_fields[header_field]['description']


    @staticmethod
    def header_type(header_field):
        """
        Return SAC header type.
        """
        return header_fields[header_field]['header_type']

    @staticmethod
    def header_undefined_value(header_field):
        """
        Return SAC heade default value.
        """
        header_type = SacHeader.header_type(header_field)
        return header_types[header_type]['undefined']

    def __get__(self, instance, owner):
        """
        Read header field from SAC file. Enumerated
        header fields are automatically translated.
        """
        instance.fh.seek(self.start)
        content = instance.fh.read(self.length)
        header_value = struct.unpack(instance._file_byteorder+self.format, content)[0]
        if isinstance(header_value, bytes):
            header_value = header_value.decode().rstrip()
        if header_value == self.undefined:
            raise ValueError('Header %s is undefined' % self.name)
        if self.is_enumerated:
            return  enumerated_header_ids[header_value]
        return header_value

    def __set__(self, instance, value):
        """
        Write header field to SAC file. Enumerated
        header fields are automatically translated.
        """
        if instance.mode == 'ro':
            raise IOError('File %s is readonly' % instance.filename)
        if value == 'undefined':
            value = self.undefined
        if self.is_enumerated and value != self.undefined:
            if value in self.valid_enum_values:
                value = enumerated_header_values[value]
            else:
                raise ValueError('%s not an allowed value for %s' % \
                (value, self.name))
        if isinstance(value, str):
            value = value.encode()
        value = struct.pack(self.format, value)
        instance.fh.seek(self.start)
        instance.fh.write(value)
