from typing import Optional, Protocol, runtime_checkable
import numpy as np
import datetime


@runtime_checkable
class Seismogram(Protocol):
    """The `Seismogram` class defines a type for a basic seismogram as used in pysmo.

    Attributes:
        __len__: The length of the Seismogram.
        data: Seismogram data.
        sampling_rate: The sampling rate [s].
        begin_time: Seismogram begin time.
        end_time: Seismogram end time (read only).

    Examples:
        Usage for a function that takes a Seismogram compatible class instance as argument
        and returns the begin time in isoformat:

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
        ...

    @property
    def data(self) -> np.ndarray:
        ...

    @data.setter
    def data(self, value: np.ndarray) -> None:
        ...

    @property
    def begin_time(self) -> datetime.datetime:
        ...

    @begin_time.setter
    def begin_time(self, value: datetime.datetime) -> None:
        ...

    @property
    def end_time(self) -> datetime.datetime:
        ...

    @property
    def sampling_rate(self) -> float:
        ...

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        ...


@runtime_checkable
class Location(Protocol):
    """The `Location` defines surface coordinates in pysmo.

    Attributes:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
    """
    @property
    def latitude(self) -> float:
        ...

    @latitude.setter
    def latitude(self, value: float) -> None:
        ...

    @property
    def longitude(self) -> float:
        ...

    @longitude.setter
    def longitude(self, value: float) -> None:
        ...


@runtime_checkable
class Station(Location, Protocol):
    """The `Station` class defines a protocol for seismic stations in Pysmo.

    Attributes:
        name: Station name or identifier.
        network: Network nam or identifiere.
        latitude (float): Station latitude in degrees.
        longitude (float): Station longitude in degrees.
        elevation: Station elevation in metres.
    """
    @property
    def name(self) -> str:
        ...

    @name.setter
    def name(self, value: str) -> None:
        ...

    @property
    def network(self) -> Optional[str]:
        ...

    @network.setter
    def network(self, value: str) -> None:
        ...

    @property
    def elevation(self) -> Optional[float]:
        ...

    @elevation.setter
    def elevation(self, value: float) -> None:
        ...


@runtime_checkable
class Hypocenter(Location, Protocol):
    """The `Hypocenter` class defines a protocol for hypocenters in pysmo.

    Attributes:
        depth: Event depth in metres.
        latitude (float): Latitude in degrees.
        longitude (float): Longitude in degrees.
    """
    @property
    def depth(self) -> float:
        ...

    @depth.setter
    def depth(self, value: float) -> None:
        ...


@runtime_checkable
class Event(Hypocenter, Protocol):
    """The `Event` class defines a protocol for events in pysmo.

    Attributes:
        depth (float): Event depth in metres.
        latitude (float): Latitude in degrees.
        longitude (float): Longitude in degrees.
        time: Event origin time.
    """
    @property
    def time(self) -> datetime.datetime:
        ...

    @time.setter
    def time(self, value: datetime.datetime) -> None:
        ...
