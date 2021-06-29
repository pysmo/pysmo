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

from weakref import WeakKeyDictionary
import os
import yaml

__copyright__ = """
Copyright (c) 2018 Simon Lloyd
"""

# Load SAC header definitions from yaml file and store them in dicts
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r')\
        as stream:
    _HEADER_DEFS = yaml.safe_load(stream)

# Create dictionary of different header types (float, integer, enumerated,
# logical, alphanumeric, auxilary). This provides respective defaults etc.
_HEADER_TYPES = _HEADER_DEFS.pop('header_types')


# Create dictionary of all header fields. This provides start position in the
# SAC file, header type, etc.
_HEADER_FIELDS = _HEADER_DEFS.pop('header_fields')

# Each enumrated header value has a corresponding integer key.
# This creates a dictionary mapping for these values
_ENUMERATED_STR2INT = _HEADER_DEFS.pop('enumerated_header_values')
# Add the undefined key/value pair to the dictionary
_ENUMERATED_STR2INT['undefined'] = _HEADER_TYPES['i']['undefined']

# Reverse dictionary to look up enumerated strings from ID.
_ENUMERATED_INT2STR = {v: k for k, v in _ENUMERATED_STR2INT.items()}


class SacHeader():
    """
    Python descriptor class for SAC file headers. Mainly for use
    inside the SacIO class.
    """

    def __init__(self, header_field):
        # Set the name to the header field name
        self.name = header_field

        # Values are stored in a weak key dictionary with the instance as key.
        self.values = WeakKeyDictionary()

        self.__doc__ = _HEADER_FIELDS[header_field]['description']

    @property
    def default(self):
        # Initially set header field value to 0 for b, npts and delta
        # All others are set the undefined value of that header type.
        if self.name in ['b', 'npts', 'delta']:
            return 0
        return self.undefined

    @property
    def required(self):
        """
        True if this is a required header field, False otherwise.
        """
        # Is this a mandatory header field?
        try:
            required = _HEADER_FIELDS[self.name]['required']
            if required in ['true', '1', 't', 'y', 'yes', 'True', 'TRUE']:
                return True
        except KeyError:
            pass
        return False

    @property
    def protected(self):
        # Is this a protected header field (npts, e, depmin, ...)?
        try:
            protected = _HEADER_FIELDS[self.name]['protected']
            if protected in ['true', '1', 't', 'y', 'yes', 'True', 'TRUE']:
                return True
        except KeyError:
            pass
        return False

    @property
    def header_type(self):
        """
        Return SAC header type.
        """
        return _HEADER_FIELDS[self.name]['header_type']

    @property
    def undefined(self):
        """
        Returns the value of an undefined header field as stored in a SAC file.
        """
        return _HEADER_TYPES[self.header_type]['undefined']

    @property
    def enumerated(self):
        """
        Returns a True if the header field is a boolean,
        otherwise returns False.
        """
        # Enumerated header fields have the allowed_vals key in their
        # dictionary, so we can set this boolean using that.
        return bool('allowed_vals' in _HEADER_FIELDS[self.name])

    @property
    def valid_enum_values(self):
        """
        Return valid 'fancy' values for enumerated header fields
        """
        return _HEADER_FIELDS[self.name]['allowed_vals'].keys()

    @property
    def valid_enum_keys(self):
        """
        Return valid internal values for enumerated header fields.
        """
        return [int(_ENUMERATED_STR2INT[i]) for i in self.valid_enum_values]

    @property
    def start(self):
        """
        Start position in the binary sac file.
        """
        return _HEADER_FIELDS[self.name]['start']

    @property
    def format(self):
        # Some header fields have their own format that is specified
        # in the dictionary.
        try:
            return _HEADER_FIELDS[self.name]['format']
        # If there is none such header field specific format use default one
        # for that type.
        except KeyError:
            return _HEADER_TYPES[self.header_type]['format']

    @property
    def length(self):
        # Some header fields have their own length that is specified in
        # the dictionary.
        try:
            return _HEADER_FIELDS[self.name]['length']
        # If there is none such header field specific length use
        # default one for that type.
        except KeyError:
            return _HEADER_TYPES[self.header_type]['length']

    @staticmethod
    def enumerated_str2int(value):
        """
        Return integer corresponding to enumerated header
        """
        return _ENUMERATED_STR2INT[value]

    def __get__(self, instance, owner):
        """
        Read header field from SAC file. Enumerated header fields are
        automatically translated from the internal integer to the
        descriptive sting.
        """
        # instance attribute accessed on class, return self
        if instance is None:
            return self

        _value = self.values.get(instance, self.default)

        if _value == self.undefined:
            return None

        if self.enumerated:
            return _ENUMERATED_INT2STR[int(_value)]

        try:
            return _value.rstrip()
        except AttributeError:
            return _value

    def __set__(self, instance, value):
        """
        Set SAC header field. Enumerated header fields are automatically
        translated. Some header fields should not be altered,
        as they depend on others (e.g. npts has to be the number of points
        in the data vector, so it doesn't make sense to change it).
        """

        # Since we sometimes DO need to change protected header fields
        # (e.g. when changing the data), we allow force setting the
        # header field if the instance.force == True. This typically
        # should not have to be used outside of sacfile.py

        if self.protected and not instance.force:
            raise ValueError('%s may not be set manualy' % self.name)

        # Set header field to type specific undefined value if required.
        elif value in ('undefined', self.undefined, None):
            self.values[instance] = self.undefined

        # Save integer corresponding to enumerated value internally.
        elif self.enumerated:
            if value in self.valid_enum_values:
                self.values[instance] = _ENUMERATED_STR2INT[value]
            elif value in self.valid_enum_keys:
                self.values[instance] = value
            else:
                raise ValueError('%s not a valid value for %s' %
                                 (value, self.name))

        # Save headers of type 'f' as a float.
        elif self.header_type == 'f':
            try:
                self.values[instance] = float(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type\
                                 float.' % (self.name, value))

        # Save headers of type 'n' as an int.
        elif self.header_type == 'n':
            try:
                self.values[instance] = int(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type\
                                 int.' % (self.name, value))

        # Save headers of type 'l' - raise an error if value is not a bool.
        elif self.header_type == 'l':
            if isinstance(value, bool):
                self.values[instance] = value
            else:
                raise ValueError('Unable to set %s to %s - must be of type\
                                 bool.' % (self.name, value))

        # Save headers of type 'k' as a string. Also check length is not
        # exceeded. Strings are also padded with spaces to match the sac
        # header length.
        elif self.header_type == 'k':
            if isinstance(value, bool):
                raise ValueError('Value for %s may not be a bool.' % self.name)
            try:
                value = str(value)
            except ValueError:
                raise ValueError('Unable to set %s to %s - must be of type\
                                 str.' % (self.name, value))
            if len(value) > self.length:
                raise ValueError('%s is too long - maximum length is %s' %
                                 (value, self.length))
            else:
                self.values[instance] = '{0: <{1}}'.format(value, self.length)

        # Catchall
        else:
            raise ValueError("%s - I don't know what to do with that header!" %
                             self.name)

        # Calculate new end time 'e' when 'b' or 'delta' are changed.
        # Only do this when instance.force is False, because we do not
        # want to trigger this when e.g. reading from a sac file.
        if self.name in ('b', 'delta') and not instance.force:
            b = instance.b
            npts = instance.npts
            delta = instance.delta
            with instance._force_set_header():
                instance.e = b + (npts - 1) * delta

    def __delete__(self, instance):
        del self.values[instance]
