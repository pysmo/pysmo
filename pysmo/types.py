from typing import Optional, Protocol, runtime_checkable
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
        >>> my_seismogram = my_sac.Seismogram
        >>> example_function(my_seismogram)
        '2005-03-02T07:23:02.160000'
    """

    def __len__(self) -> int:
        """Returns the length (number of points) of a Seismogram."""
        ...

    @property
    def data(self) -> np.ndarray:
        """Seismogram data stored as numpy array."""
        ...

    @data.setter
    def data(self, value: np.ndarray) -> None:
        ...

    @property
    def begin_time(self) -> datetime.datetime:
        """Seismogram begin time."""
        ...

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        ...

    @property
    def end_time(self) -> datetime.datetime:
        """Seismogram end time"""
        ...

    @property
    def sampling_rate(self) -> float:
        """Seismogram sampling rate."""
        ...

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        ...


@runtime_checkable
class Location(Protocol):
    """The :class:`Location` defines surface coordinates in pysmo."""
    @property
    def latitude(self) -> float:
        """Latitude in degrees."""
        ...

    @latitude.setter
    def latitude(self, value: float) -> None:
        ...

    @property
    def longitude(self) -> float:
        """Longitude in degrees."""
        ...

    @longitude.setter
    def longitude(self, value: float) -> None:
        ...


@runtime_checkable
class Station(Location, Protocol):
    """The :class:`Station` class defines a protocol for seismic stations in Pysmo.
    """
    @property
    def name(self) -> str:
        """Station name."""
        ...

    @name.setter
    def name(self, value: str) -> None:
        ...

    @property
    def network(self) -> str:
        """Station network name."""
        ...

    @network.setter
    def network(self, value: str) -> None:
        ...

    @property
    def elevation(self) -> Optional[float]:
        """Station elevation in metres."""
        ...

    @elevation.setter
    def elevation(self, value: float) -> None:
        ...


@runtime_checkable
class Hypocenter(Location, Protocol):
    """The :class:`Hypocenter` class defines a protocol for hypocenters in pysmo.
    """
    @property
    def depth(self) -> float:
        """Event depth in metres."""
        ...

    @depth.setter
    def depth(self, value: float) -> None:
        ...
