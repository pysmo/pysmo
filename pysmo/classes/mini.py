import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS


@dataclass
class MiniSeismogram:
    """Minimal class for seismogram data.

    The :py:class:`MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the :py:class:`Seismogram` type.

    Example usage::

        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime
        >>> import numpy as np
        >>> my_seismogram = MiniSeismogram(begin_time=datetime.now(),sampling_rate=0.1,
                                           data=np.random.rand(100), id='myseis')
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = SEISMOGRAM_DEFAULTS.begin_time
    """Seismogram begin time.

    The :py:attr:`MiniSeismogram.begin_time` attribute is the (absolute) time of the
    first element of the seismogram data stored in :py:attr:`MiniSeismogram.data`.
    If a new instance is created without specifiying the begin time, Unix time 0 is used.
    """

    sampling_rate: float = SEISMOGRAM_DEFAULTS.sampling_rate
    """Seismogram sampling rate.

    The :py:attr:`MiniSeismogram.sampling_rate` attribute is the sampling rate of the
    seismogram in seconds. If a new instance is created without specifiying the sampling
    rate, a default value of 1s is used.
    """

    data: np.ndarray = field(default_factory=lambda: np.array([]))
    """Seismogram data.

    The :py:attr:`data` attribute is a numpy array containing seismogram
    data. If a new instance is created without specifiying the data an empty array is
    used.
    """

    id: Optional[str] = None
    """Seismogram ID.

    :py:attr:`id` is an optional attribute to store an identifier in.
    """

    def __len__(self) -> int:
        """Read only attribute tat returns the length (number of points) of a
        seismogram."""
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        """Seismogram end time.

        The :py:attr:`end_time` attribute is a read only attribute that
        returns the seismogram end time.
        """
        return self.begin_time + timedelta(seconds=self.sampling_rate*(len(self)-1))


@dataclass
class MiniLocation:
    """Minimal class for geographical locations.

    The :py:class:`MiniLocation` class provides a minimal implementation of class that
    is compatible with the :py:class:`Location` type.

    Example usage::

        >>> from pysmo import MiniLocation, Location
        >>> my_location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>> isinstance(my_location, Location)
        True
    """

    latitude: float
    """The latitude of an object from -90 to 90 degrees."""

    longitude: float
    """The longitude of an object from -180 to 180 degrees."""


@dataclass
class MiniStation(MiniLocation):
    """Minimal class for seismic stations.

    The :py:class:`MiniStation` class provides a minimal implementation of class that
    is compatible with the :py:class:`Station` type. The class is a subclass of
    :py:class:`MiniLocation`, and therefore also matches the :py:class:`Location` type.

    Example usage::

        >>> from pysmo import MiniStation, Station, Location
        >>> my_station = MiniStation(latitude=-21.680301, longitude=-46.732601,
                                     name="CACB", network="BL")
        >>> isinstance(my_station, Station)
        True
        >>> isinstance(my_station, Location)
        True
    """
    name: str
    """Station name.

    The :py:attr:`name` attribute stores the station name.
    """

    network: str
    """Network name.

    The :py:attr:`network` attribute stores the network name.
    """

    elevation: Optional[float] = None
    """Station elevation.

    The :py:attr:`elevation` attribute stores the station elevation in metres.
    """


@dataclass
class MiniHypocenter(MiniLocation):
    """Minimal class for hypocententers.

    The :py:class:`MiniHypocenter` class provides a minimal implementation of class that
    is compatible with the :py:class:`Hypocenter` type. The class is a subclass of
    :py:class:`MiniLocation`, and therefore also matches the :py:class:`Location` type.
    Example usage::

        >>> from pysmo import MiniHypocenter, Hypocenter, Location
        >>> my_hypo = MiniHypocenter(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(my_hypo, Hypocenter)
        True
        >>> isinstance(my_hypo, Location)
        True
    """

    depth: float
    """
    Hypocenter depth.

    The :py:attr:`depth` attribute stores the hypocenter depth in metres.
    """
