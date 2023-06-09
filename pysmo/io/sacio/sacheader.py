from __future__ import annotations

__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"

import os
import yaml
from abc import ABC, abstractmethod

# Read yaml file with dictionaries describing SAC headers
with open(os.path.join(os.path.dirname(__file__), 'sacheader.yml'), 'r') as stream:
    _HEADER_DEFS: dict = yaml.safe_load(stream)

# Dictionary of header types (default values etc)
HEADER_TYPES: dict = _HEADER_DEFS.pop('header_types')
# Dictionary of header fields (format, type, etc)
HEADER_FIELDS: dict = _HEADER_DEFS.pop('header_fields')
# Dictionary of enumerated headers (to convert int to str).
ENUM_DICT: dict = _HEADER_DEFS.pop('enumerated_header_values')


class SacHeader(ABC):
    """Python descriptor (abstract)class for SAC file headers."""
    # Tuple of read-only header fields
    read_only_headers = tuple([header_field for header_field in HEADER_FIELDS if
                               HEADER_FIELDS[header_field].get('read_only', False) is True])

    def __set_name__(self, owner, name: str) -> None:  # type: ignore
        self.public_name: str = name
        self.private_name: str = '_' + name

    def __get__(self, obj, objtype=None):  # type: ignore
        # instance attribute accessed on class, return self
        if obj is None:
            return self

        # The private_value content is in the same format as in a SAC file.
        private_value = getattr(obj, self.private_name)

        # Instead of returning SAC unknown placeholders (e.g. -12345) we return None
        if private_value == HEADER_TYPES[self.header_type]['undefined']:
            return None

        # Format value before returning. This will also translate enumerated headers.
        return self.format2public(private_value)

    def __set__(self, obj, public_value):  # type: ignore
        # Setting the public value to None updates the private value to be the 'undefined'
        # value for that header field. Since this only really is used during initialisation
        # of a SAC instance we don't check for read-only header values.
        if public_value is None:
            setattr(obj, self.private_name, HEADER_TYPES[self.header_type]['undefined'])

        # Format to SAC format and save to private_name
        else:
            # Some headers are calculated from data/other headers, and should not be set.
            if self.public_name in self.read_only_headers:
                raise RuntimeError(f"{self.public_name} is a read-only header field.")

            # Set attribute in SAC internal format.
            setattr(obj, self.private_name, self.validate_and_format2private(public_value))

            # Changing b or delta requires recomputing end time e
            if self.public_name in ('b', 'delta'):
                obj._e = obj.b + (obj.npts - 1) * obj.delta

    @abstractmethod
    def validate_and_format2private(self, public_value):  # type: ignore
        """First validates a public value, then converts it to the respective private value (i.e. SAC internal)."""
        pass

    @abstractmethod
    def format2public(self, private_value):  # type: ignore
        """Format a private value (SAC internal format) to a public value format."""
        pass

    @property
    @abstractmethod
    def header_type(self) -> str:
        """Returns the SAC header type (k, f, ...)."""
        pass

    @property
    def sac_start_position(self) -> int:
        """Returns the start position in the binary sac file."""
        return int(HEADER_FIELDS[self.public_name]['start'])

    @property
    def sac_length(self) -> int:
        """Returns length to read from SAC file."""
        # Some header fields have their own length that is specified in the dictionary.
        try:
            return int(HEADER_FIELDS[self.public_name]['length'])
        # If there is none such header field specific format use default one for that type.
        except KeyError:
            return int(HEADER_TYPES[self.header_type]['length'])

    @property
    def sac_format(self) -> str:
        """Returns the SAC format used to write headers to a SAC file."""
        # Some header fields have their own format that is specified in the dictionary.
        try:
            return HEADER_FIELDS[self.public_name]['format']
        # If there is none such header field specific format use default one for that type.
        except KeyError:
            return HEADER_TYPES[self.header_type]['format']


class SacFloatHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        return HEADER_FIELDS[self.public_name]['description']

    @property
    def header_type(self) -> str:
        return ('f')

    def validate_and_format2private(self, public_value: float | int) -> float:
        if not isinstance(public_value, float | int):
            raise TypeError(f"Setting {self.public_name} to {public_value} failed. " +
                            f"Expected float, got {type(public_value)}.")
        if self.public_name in ("evla", "stla") and not 90 >= public_value >= -90:
            raise ValueError(f"Setting {self.public_name} to {public_value} failed. " +
                             "Latitude must be no smaller than -90 and no greater than 90.")
        elif self.public_name in ("evlo", "stlo") and not 180 >= public_value >= -180:
            raise ValueError(f"Setting {self.public_name} to {public_value} failed. " +
                             "Longitude must be no smaller than -180 and no greater than 180.")
        return float(public_value)

    def format2public(self, private_value: float) -> float:
        return float(private_value)


class SacIntHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        return HEADER_FIELDS[self.public_name]['description']

    @property
    def header_type(self) -> str:
        return ('n')

    def validate_and_format2private(self, public_value: int) -> int:
        if not isinstance(public_value, int):
            raise TypeError(f"trying to set {self.public_name} to {public_value} failed.\
                            Expected int, got {type(public_value)}.")
        return int(public_value)

    def format2public(self, private_value: int) -> int:
        return int(private_value)


class SacEnumeratedHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        doc = HEADER_FIELDS[self.public_name]['description']
        try:
            allowed_vals = HEADER_FIELDS[self.public_name]['allowed_vals']
            doc += f"\n\n {self.public_name} must be one of:\n"
            for val, desc in allowed_vals.items():
                doc += f"\n  - {val}:  {desc}"
        except KeyError:
            pass
        return doc

    @property
    def header_type(self) -> str:
        return ('i')

    def validate_and_format2private(self, public_value: str) -> int:
        # Convert from string to int
        return ENUM_DICT[public_value]

    def format2public(self, private_value: int) -> str:
        # convert from int to string
        int2str_dict = {v: k for k, v in ENUM_DICT.items()}
        return int2str_dict[private_value]


class SacLogicalHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        return HEADER_FIELDS[self.public_name]['description']

    @property
    def header_type(self) -> str:
        return ('l')

    def validate_and_format2private(self, public_value: bool) -> bool:
        if not isinstance(public_value, bool):
            raise TypeError(f"trying to set {self.public_name} to {public_value} failed.\
                            Expected bool, got {type(public_value)}.")
        return public_value

    def format2public(self, private_value: bool) -> bool:
        if isinstance(private_value, bool):
            return private_value


class SacAlphanumericHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        return HEADER_FIELDS[self.public_name]['description']

    @property
    def header_type(self) -> str:
        return ('k')

    def validate_and_format2private(self, public_value: str) -> str:
        if isinstance(public_value, bool):
            raise TypeError(f"{self.public_name} may not be of type bool")
        if len(public_value) > self.sac_length:
            raise ValueError(f"{public_value} is too long - maximum length for {self.public_name} is {self.sac_length}")
        return str(public_value)

    def format2public(self, private_value: str) -> str:
        return str(private_value).rstrip()


class SacAuxHeader(SacHeader):
    @property
    def __doc__(self):  # type: ignore
        return HEADER_FIELDS[self.public_name]['description']

    @property
    def header_type(self) -> str:
        return ('a')

    def validate_and_format2private(self, public_value):  # type: ignore
        raise RuntimeError(f"I don't know how to format {self.public_name}!")

    def format2public(self, private_value):  # type: ignore
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
    header_type = HEADER_FIELDS[header_name]['header_type']
    return header_map[header_type]
