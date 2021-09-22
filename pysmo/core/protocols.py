"""
Protocols
---------

Pysmo uses `Python Protocol classes <https://docs.python.org/3/library/typing.html#typing.Protocol>`_
to define what attributes and methods *e.g*. a "seismogram" class should contain. These definitions
are in no way meant to be comprehensive, and most definitely do not attempt to account for all the
fields, variables, etc. one might find in various seismogram (file) formats. We feel this would lead
to a complex, and potentially hard to maintain data construct containing way more information than
typically required. Instead the definitions are entirely driven by the requirements coming from
the pysmo functions themselves. The protocols thus provide an interface between data and pysmo
functions. The main implications of this approach are:

*   The different types of data available to pysmo functions via the protocols are
    well defined, making it very straightforward to write new functions that are
    compatible with pysmo.
*   No need for a "native" pysmo data class, which would likely require importing (and
    exporting) data from other formats. Instead, existing formats can be extended to
    become compatible with pysmo protocols. Unlike importing, this means there is no
    need to consider parts of the existing formats that are not being used by pysmo, or
    how to convert between different formats.
*   Since traditional file formats contain a lot of metadata, the corresponding data classes
    in pysmo will often match multiple protocol types. Occasionally this means the same arguments
    need to be passed to functions more than once (e.g. when a function requires one Event type
    argument and one Station type argument, and both happen to be provided by the same data class).

.. note::
    Python does not perform run-time type checking (though there are libraries that can provide this).
    There is therefore nothing stopping a user from trying to execute a function with input arguments of
    the wrong type. We therefore highly recommend adding type hints to code and testing it with
    *e.g.* `mypy <https://mypy.readthedocs.io/en/stable>`_.

The protocol classes used in pysmo are described below:
"""

from typing import Protocol
import numpy as np
import datetime


class Seismogram(Protocol):
    """The :class:`Seismogram` class defines a protocol for a basic seismogram as used in pysmo.

    Example usage for a function that takes a Seismogram compatible class instance as argument
    and returns the begin time in isoformat::

        >>> from pysmo import SAC, Seismogram  # SAC is a class that "speaks" Seismogram
        >>> def begin_time_in_isoformat(seis_in: Seismogram) -> str:
        ...     return seis_in.begin_time.isoformat()
        ...
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> example_function(my_sac)
        '2005-03-02T07:23:02.160000'
    """
    def __len__(self) -> int:
        pass

    @property
    def data(self) -> np.ndarray:
        """Returns the seismogram data as numpy array."""
        pass

    @data.setter
    def data(self, value: np.ndarray) -> None:
        """Sets the data."""
        pass

    @property
    def begin_time(self) -> datetime.datetime:
        """Returns the begin time"""
        pass

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        """Returns the begin time"""
        pass

    @property
    def end_time(self) -> datetime.datetime:
        """Returns the end time"""
        pass

    @property
    def sampling_rate(self) -> float:
        """Returns sampling rate."""
        pass

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        """Sets the sampling rate."""
        pass

    @property
    def id(self) -> str:
        """Returns seismogram id string"""
        pass


class Station(Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in pysmo.
    """
    @property
    def name(self) -> str:
        """Gets the station name."""
        pass

    @name.setter
    def name(self, value: str) -> None:
        """Sets the station name."""
        pass

    @property
    def station_latitude(self) -> float:
        """Gets the station latitude."""
        pass

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        """Sets the station latitude."""
        pass

    @property
    def station_longitude(self) -> float:
        """Gets the station longitude."""
        pass

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        """Sets the station longitude."""
        pass

    @property
    def station_elevation(self) -> float:
        """Gets the station elevation."""
        pass

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        """Sets the station elevation."""
        pass


class Event(Protocol):
    """The :class:`Event` class defines a protocol for seismic events in pysmo.
    """
    @property
    def event_latitude(self) -> float:
        """Gets the event latitude."""
        pass

    @event_latitude.setter
    def event_latitude(self, value: float) -> None:
        """Sets the event latitude."""
        pass

    @property
    def event_longitude(self) -> float:
        """Gets the event longitude."""
        pass

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        """Sets the event longitude."""
        pass

    @property
    def event_depth(self) -> float:
        """Gets the event depth."""
        pass

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        pass
