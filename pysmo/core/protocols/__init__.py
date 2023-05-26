"""
Seismograms are often distributed as a time series paired with large amounts
of metadata. Depending on what information is used for further processing,
metadata may well become more important than the time series itself. Conversely,
metadata could also be completely irrelevant if only the time series data are used.
Therefore we consider metadata and time series data to be independent and
equally important data types in pysmo. These data types are defined using
`Python Protocol classes <https://docs.python.org/3/library/typing.html#typing.Protocol>`_,
and serve as input and output for pysmo functions. Some things to keep in
mind are:

*   Pysmo is not built on top of a particular file format or
    corresponding Python data class to store data in (nor does
    not provide it's own format). Instead it relies on existing
    data classes to be either compatible out of the box, or (as
    is usually the case) extended to become so.
*   Pysmo protocols only prescribe what information has to be
    present in a data class, but do not limit what information
    may be stored in them. As pysmo protocols are defined quite
    narrowly and data classes often are often quite broad, a single
    data class may well be used as different types of input with
    pysmo functions.
*   Python does not perform run-time type checking (though there
    are libraries that can provide this). There is therefore nothing
    stopping a user from trying to execute a function with input
    arguments of the wrong type. We therefore highly recommend
    adding type hints to code and testing it with *e.g.*
    `mypy <https://mypy.readthedocs.io/en/stable>`_.

The protocol classes used in Pysmo are described below:
"""

from .seismogram import Seismogram
from .station import Station
from .epicenter import Epicenter
from .hypocenter import Hypocenter

__all__ = [
    'Seismogram',
    'Station',
    'Epicenter',
    'Hypocenter'
]
