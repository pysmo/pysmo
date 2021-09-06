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

from abc import ABC, abstractproperty
import os
import yaml

__copyright__ = """
Copyright (c) 2018 Simon Lloyd
"""

with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _HEADER_DEFS = yaml.safe_load(stream)

HEADER_TYPES = _HEADER_DEFS.pop('header_types')
HEADER_FIELDS = _HEADER_DEFS.pop('header_fields')
ENUM_DICT = _HEADER_DEFS.pop('enumerated_header_values')


class SacHeader(ABC):
    """
    Python descriptor class for SAC file headers. Mainly for use inside the SacIO class.
    """
    # create a list of read-only header fields
    read_only_headers = [header_field for header_field in HEADER_FIELDS.keys() if
                         HEADER_FIELDS[header_field].get('read_only', False) is True]

    @property
    def __doc__(self):
        return HEADER_FIELDS[self.public_name]['description']

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = '_' + name

    def __get__(self, obj, objtype=None):
        # instance attribute accessed on class, return self
        if obj is None:
            return self

        # The private_value content is in the same format as in a SAC file.
        private_value = getattr(obj, self.private_name)

        # Return None for uknown header values
        if private_value == HEADER_TYPES[self.header_type]['undefined']:
            return None

        # Format value before returning. This will also translate enumerated headers.
        return self.format2public(private_value)

    def __set__(self, obj, public_value):
        # Setting the public value to None updates the private value to be the 'undefined'
        # value for that header field. Since this only really is used during initialisation
        # of a SacIO instance we don't check for read-only header values.
        if public_value is None:
            setattr(obj, self.private_name, HEADER_TYPES[self.header_type]['undefined'])

        # Format to SAC format and save to private_name
        else:
            # Some headers are calculated from data/other headers, and should not be set.
            if self.public_name in self.read_only_headers:
                raise RuntimeError(f"{self.public_name} is a read-only header field.")

            # Set attribute in SAC internal format.
            setattr(obj, self.private_name, self.validate_and_format2private(public_value))
            if self.public_name in ('b', 'delta'):
                obj._e = obj.b + (obj.npts - 1) * obj.delta

    @abstractproperty
    def validate_and_format2private(self, public_value):
        pass

    @abstractproperty
    def format2public(self, private_value):
        pass

    @abstractproperty
    def header_type(self):
        pass

    @property
    def sac_start_position(self):
        """
        Start position in the binary sac file.
        """
        return HEADER_FIELDS[self.public_name]['start']

    @property
    def sac_length(self) -> int:
        """
        Returns length to read from SAC file.
        """
        # Some header fields have their own length that is specified in the dictionary.
        try:
            return HEADER_FIELDS[self.public_name]['length']
        # If there is none such header field specific format use default one for that type.
        except KeyError:
            return HEADER_TYPES[self.header_type]['length']

    @property
    def sac_format(self):
        # Some header fields have their own format that is specified in the dictionary.
        try:
            return HEADER_FIELDS[self.public_name]['format']
        # If there is none such header field specific format use default one for that type.
        except KeyError:
            return HEADER_TYPES[self.header_type]['format']


class SacFloatHeader(SacHeader):
    """
    Subclass for Float ('f') type SAC headers.
    """

    @property
    def header_type(self):
        return('f')

    def validate_and_format2private(self, public_value):
        return float(public_value)

    def format2public(self, private_value):
        return float(private_value)


class SacIntHeader(SacHeader):
    """
    Subclass for Integer ('n') type SAC headers.
    """

    @property
    def header_type(self):
        return('n')

    def validate_and_format2private(self, public_value):
        return int(public_value)

    def format2public(self, private_value):
        return int(private_value)


class SacEnumeratedHeader(SacHeader):
    """
    Subclass for Enumerated ('i') type SAC headers.
    """

    @property
    def header_type(self):
        return('i')

    def validate_and_format2private(self, public_value):
        # Convert from string to int
        return ENUM_DICT[public_value]

    def format2public(self, private_value):
        # convert from int to string
        int2str_dict = {v: k for k, v in ENUM_DICT.items()}
        return int2str_dict[private_value]


class SacLogicalHeader(SacHeader):
    """
    Subclass for Logical ('l') type SAC headers.
    """

    @property
    def header_type(self):
        return('l')

    def validate_and_format2private(self, public_value):
        if isinstance(public_value, bool):
            return public_value

    def format2public(self, private_value):
        if isinstance(private_value, bool):
            return private_value


class SacAlphanumericHeader(SacHeader):
    """
    Subclass for Alphanumeric ('k') type SAC headers.
    """

    @property
    def header_type(self):
        return('k')

    def validate_and_format2private(self, public_value):
        if isinstance(public_value, bool):
            raise ValueError(f"{self.public_name} may not be of type bool")
        if len(public_value) > self.sac_length:
            raise ValueError(f"{public_value} is too long - maximum length for {self.public_name} is {self.sac_length}")
        return str(public_value)

    def format2public(self, private_value):
        return str(private_value).rstrip()


class SacAuxHeader(SacHeader):
    """
    Subclass for Auxiliary ('a') type SAC headers.
    """

    @property
    def header_type(self):
        return('a')

    def validate_and_format2private(self, public_value):
        raise RuntimeError(f"I don't know how to format {self.public_name}!")

    def format2public(self, private_value):
        raise RuntimeError(f"I don't know how to format {self.public_name}!")
