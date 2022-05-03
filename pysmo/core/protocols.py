"""
Protocols
---------

A core principle of pysmo (or more specifically pysmo functions), is to be agnostic with regards to
the types of data files used. In the vast majority of cases, a function processing data stored in a
file of a certain type will only use a fraction of the data contained in the file itself. This is
particularly the case when additional metadata is stored alongside e.g. a time series. Therefore,
instead of defining python classes that essentially turn a file into an equivalent python object
that consumes all data and logic contained within the file, pysmo uses `Python Protocol classes
<https://docs.python.org/3/library/typing.html#typing.Protocol>`_ to define what attributes and
methods classes should contain. These class definitions are are entirely driven by the requirements
coming from the pysmo functions themselves, rather than what is stored in files of a particular format.
The protocols thus provide an interface between data and pysmo functions. The main benefits and
implications of this approach are:

*   Files of various formats still need to be read into python classes to be used with pysmo,
    but the way they are allowed to be used is determined entirely by the protocols matched
    by these classes. In other words, compatibility of multiple file formats with pysmo functions
    can be guaranteed (so much so that mixing and matching different file formats in the same
    function is seamlessly possible).
*   The different types of data classes available to pysmo functions via the protocols are well
    defined and typically much simpler than the file format used to store the data, making it very
    straightforward to use, maintain and extend pysmo.
*   No need for a "native" pysmo data class, which would likely require importing (and exporting)
    data from other formats. Instead, existing formats can be extended to become compatible with
    pysmo protocols. Unlike importing, this means there is no need to consider parts of the
    existing formats that are not being used by pysmo, or how to convert between different formats.
*   Since traditional file formats contain a lot of metadata, the corresponding data classes in
    pysmo will often match multiple protocol types. In cases where functions require
    Occasionally this means the same arguments
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
