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
class Location(Protocol):
    """The :class:`Location` defines surface coordinates in pysmo."""
    @property
    def latitude(self) -> float:
        """Returns the latitude."""
        ...

    @latitude.setter
    def latitude(self, value: float) -> None:
        """Sets the latitude."""
        ...

    @property
    def longitude(self) -> float:
        """Returns the longitude."""
        ...

    @longitude.setter
    def longitude(self, value: float) -> None:
        """Sets the longitude."""
        ...


@runtime_checkable
class Station(Location, Protocol):
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
    def network(self) -> str:
        """Retuns the station network."""
        ...

    @network.setter
    def network(self, value: str) -> None:
        """Sets the station network."""
        ...
    #
    # @property
    # def latitude(self) -> float:
    #     """Retuns the station latitude."""
    #     ...
    #
    # @latitude.setter
    # def latitude(self, value: float) -> None:
    #     """Sets the station latitude."""
    #     ...
    #
    # @property
    # def longitude(self) -> float:
    #     """Retuns the station longitude."""
    #     ...
    #
    # @longitude.setter
    # def longitude(self, value: float) -> None:
    #     """Sets the station longitude."""
    #     ...

    @property
    def elevation(self) -> float:
        """Retuns the station elevation."""
        ...

    @elevation.setter
    def elevation(self, value: float) -> None:
        """Sets the station elevation."""
        ...


@runtime_checkable
class Hypocenter(Location, Protocol):
    """The :class:`Hypocenter` class defines a protocol for hypocenters in pysmo.
    """
    @property
    def depth(self) -> float:
        """Returns the event depth."""
        ...

    @depth.setter
    def depth(self, value: float) -> None:
        """Sets the event depth."""
        ...
