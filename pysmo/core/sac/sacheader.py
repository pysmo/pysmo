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

# Load SAC header definitions from yaml file and store them in dicts
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _header_defs = yaml.load(stream)

# Create dictionary of different header types (float, integer, enumerated, logical,
# alphanumeric, auxilary). This provides respective defaults etc.
header_types = _header_defs.pop('header_types')


# Create dictionary of all header fields. This provides start position in the 
# SAC file, header type, etc.
header_fields = _header_defs.pop('header_fields')

# Each enumrated header value has a corresponding integer key. 
# This creates a dictionary mapping these values
enumerated_header_val2key = _header_defs.pop('enumerated_header_values')
# Add the undefined key/value pair to the dictionary
enumerated_header_val2key['undefined'] = header_types['i']['undefined']

# Reverse dictionary to look up enumerated strings from ID.
enumerated_header_key2val = {v: k for k, v in enumerated_header_val2key.items()}


class SacHeader(object):
    """
    Python descriptor class for SAC file headers. Mainly for use
    inside the SacIO class.
    """

    def __init__(self, header_field):
        # Set the name to the header field name
        self.name = header_field

        # Start position in the binary sac file
        self.start = header_fields[header_field]['start']

        # Set the type of sac header
        self.header_type = SacHeader.header_type(header_field)

        # Is this a mandatory header field?
        try:
            self.required = header_fields[header_field]['required']
        except KeyError:
            self.required = False

        # Is this a protected header field (npts, e, depmin, ...)?
        try:
            self.protected = header_fields[header_field]['protected']
        except KeyError:
            self.protected = False

        # Initially set header field value to the undefined value of that header type.
        self.undefined = header_types[self.header_type]['undefined']
        self._value = self.undefined


        # Enumerated header fields have the allowed_vals key in their dictionary, so
        # we can set this boolean using that.
        self.is_enumerated = bool('allowed_vals' in header_fields[header_field])
        if self.is_enumerated:
            # Valid 'fancy' values for this header field
            self.valid_enum_values = header_fields[header_field]['allowed_vals'].keys()
            # Valid internal values for this header field
            self.valid_enum_keys = [enumerated_header_val2key[i] for i in self.valid_enum_values]


        # Save valid values for enumerated header fields.
        if self.is_enumerated:
            # list of valid values
            self.valid_enum_values = header_fields[header_field]['allowed_vals'].keys()

        # Some header fields have their own format that is specified in the dictionary.
        try:
            self.format = header_fields[header_field]['format']
        # If there is none such header field specific format use default one for that type.
        except KeyError:
            self.format = header_types[self.header_type]['format']

        # Some header fields have their own length that is specified in the dictionary.
        try:
            self.length = header_fields[header_field]['length']
        # If there is none such header field specific length use default one for that type.
        except KeyError:
            self.length = header_types[self.header_type]['length']

        # Store the header description in the docstring.
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
        Read header field from SAC file. Enumerated header fields are automatically
        translated from the internal integer to the descriptive sting.
        """
        # instance attribute accessed on class, return self
        if instance is None:
            return self
        elif self._value == self.undefined:
            raise ValueError('Header %s is undefined' % self.name)
        elif self.is_enumerated:
            return  enumerated_header_key2val[self._value]
        try:
            return self._value.rstrip()
        except:
            return self._value

    def __set__(self, instance, value):
        """
        Write header field to SAC file. Enumerated header fields are
        automatically translated. Some header fields should not be altered,
        as they depend on others (e.g. npts has to be the number of points
        in the data vector, so it doesn't make sense to change it).
        """

        # Since we sometimes DO need to change protected header fields
        # (e.g. when changing the data), we allow force setting the 
        # header field if the value is a tuple, with the 2nd item
        # set to 'True'. This typically should not have to be used
        # outside of sacfile.py
        if isinstance(value, tuple):
            value, force = value
        else:
            force = False

        if self.protected and not force:
            raise ValueError('%s may not be set manualy' % self.name)


        # Set header field to type specific undefined value if required.
        elif value == 'undefined' or value == self.undefined:
            self._value = self.undefined


        # Save integer corresponding to enumerated value internally.
        elif self.is_enumerated:
            if value in self.valid_enum_values:
                self._value = enumerated_header_val2key[value]
            elif value in self.valid_enum_keys:
                self._value = value
            else:
                raise ValueError('%s not a valid value for %s' % (value, self.name))


        # Save headers of type 'f' as a float.
        elif self.header_type == 'f':
            try:
                self._value = float(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type float.' % \
                                 (self.name, value))


        # Save headers of type 'n' as an int.
        elif self.header_type == 'n':
            try:
                self._value = int(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type int.' % \
                                 (self.name, value))


        # Save headers of type 'l' - raise an error if value is not a bool.
        elif self.header_type == 'l':
            if isinstance(value, bool):
                self._value = value
            else:
                raise ValueError('Unable to set %s to %s - must be of type int.' % \
                                 (self.name, value))


        # Save headers of type 'k' as a string. Also check length is not exceeded.
        # Strings are also padded with spaces to match the sac header length.
        elif self.header_type == 'k':
            if isinstance(value, bool):
                raise ValueError('Value for %s may not be a bool.' % self.name)
            try:
                self._value = str(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type str.' % \
                                 (self.name, value))
            if len(self._value) > self.length:
                raise ValueError('%s is too long - maximum length is %s' % \
                                 (self._value, self.length))
            else:
                self._value = '{0: <{1}}'.format(self._value, self.length)
                                
        # Catchall
        else:
            raise ValueError("%s - I don't know what to do with that header!" % self.name)

        # Calculate new end time 'e' when 'b' is changed.
        if self.name == 'b' and not force:
            npts = instance.npts
            delta = instance.delta
            instance.e = (value + (npts - 1) * delta, True)
