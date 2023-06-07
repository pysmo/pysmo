from typing import Protocol, runtime_checkable
import numpy as np
import datetime


@runtime_checkable
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
        """Returns the length (number of points) of a Seismogram."""
        ...

    @property
    def data(self) -> np.ndarray:
        """Returns the seismogram data as numpy array."""
        ...

    @data.setter
    def data(self, value: np.ndarray) -> None:
        """Sets the data."""
        ...

    @property
    def begin_time(self) -> datetime.datetime:
        """Returns the begin time"""
        ...

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        """Returns the begin time"""
        ...

    @property
    def end_time(self) -> datetime.datetime:
        """Returns the end time"""
        ...

    @property
    def sampling_rate(self) -> float:
        """Returns sampling rate."""
        ...

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        """Sets the sampling rate."""
        ...


@runtime_checkable
class Station(Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in Pysmo.
    """
    @property
    def name(self) -> str:
        """Retuns the station name."""
        ...

    @name.setter
    def name(self, value: str) -> None:
        """Sets the station name."""
        ...

    @property
    def station_latitude(self) -> float:
        """Retuns the station latitude."""
        ...

    @station_latitude.setter
    def station_latitude(self, value: float) -> None:
        """Sets the station latitude."""
        ...

    @property
    def station_longitude(self) -> float:
        """Retuns the station longitude."""
        ...

    @station_longitude.setter
    def station_longitude(self, value: float) -> None:
        """Sets the station longitude."""
        ...

    @property
    def station_elevation(self) -> float:
        """Retuns the station elevation."""
        ...

    @station_elevation.setter
    def station_elevation(self, value: float) -> None:
        """Sets the station elevation."""
        ...


@runtime_checkable
class Epicenter(Protocol):
    """The :class:`Epicenter` defines an epicenter in pysmo.
    """
    @property
    def event_latitude(self) -> float:
        """Returns the event latitude."""
        ...

    @event_latitude.setter
    def event_latitude(self, value: float) -> None:
        """Sets the event latitude."""
        ...

    @property
    def event_longitude(self) -> float:
        """Returns the event longitude."""
        ...

    @event_longitude.setter
    def event_longitude(self, value: float) -> None:
        """Sets the event longitude."""
        ...


@runtime_checkable
class Hypocenter(Epicenter, Protocol):
    """The :class:`Hypocenter` class defines a protocol for hypocenters in pysmo.
    """
    @property
    def event_depth(self) -> float:
        """Returns the event depth."""
        ...

    @event_depth.setter
    def event_depth(self, value: float) -> None:
        """Sets the event depth."""
        ...
