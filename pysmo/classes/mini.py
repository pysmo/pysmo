"""
Pysmo includes a minimal implementations of a class for each type. They are all named
using the pattern `Mini<Type>`, thus the [`Seismogram`][pysmo.types.Seismogram] type has
a corresponding [`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] class. The *Mini*
classes may be used directly to store and process data, or serve as base classes when
creating new or modifying existing classes.
"""
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.lib.functions import (
    _normalize,
    _detrend,
    _resample
)


@dataclass
class MiniSeismogram:
    """Minimal class for seismogram data.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the `Seismogram` type.

    Attributes:
        begin_time: Seismogram begin time.
        end_time: Seismogram end time.
        sampling_rate: Seismogram sampling rate.
        data: Seismogram data.
        id: Optional identifier

    Examples:
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime
        >>> import numpy as np
        >>> my_seismogram = MiniSeismogram(begin_time=datetime.now(),sampling_rate=0.1,
                                           data=np.random.rand(100), id='myseis')
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = SEISMOGRAM_DEFAULTS.begin_time
    sampling_rate: float = SEISMOGRAM_DEFAULTS.sampling_rate
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    id: Optional[str] = None

    def __len__(self) -> int:
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        return self.begin_time + timedelta(seconds=self.sampling_rate*(len(self)-1))

    def normalize(self) -> None:
        """Normalize the seismogram data with its absolute max value.

        Examples:
            >>> import numpy as np
            >>> from pysmo import MiniSeismogram
            >>> my_seis = MiniSeismogram(data=np.array([5, 3, 7]))
            >>> my_seis.normalize()
            >>> my_seis.data
            array([0.71428571, 0.42857143, 1.        ])
        """
        self.data = _normalize(self)

    def detrend(self) -> None:
        """Remove linear and/or constant trends from a seismogram.

        Examples:
            >>> import numpy as np
            >>> import pytest
            >>> from pysmo import MiniSeismogram
            >>> my_seis = MiniSeismogram(data=np.array([5, 3, 7]))
            >>> my_seis.detrend()
            >>> np.mean(my_seis.data)
            >>> assert 0 == pytest.approx(np.mean(my_seis.data))
            True
        """
        self.data = _detrend(self)

    def resample(self, sampling_rate: float) -> None:
        """Resample Seismogram object data using the Fourier method.

        Parameters:
            sampling_rate: New sampling rate.

        Examples:
            >>> from pysmo import MiniSeismogram
            >>> my_seis = MiniSeismogram(data=np.random.rand(10000))
            >>> len(my_seis)
            10000
            >>> new_sampling_rate = my_seis.sampling_rate * 2
            >>> my_seis.resample(new_sampling_rate)
            >>> len(my_seis)
            5000
        """
        self.data, self.sampling_rate = _resample(self, sampling_rate), sampling_rate


@dataclass
class MiniLocation:
    """Minimal class for geographical locations.

    The `MiniLocation` class provides a minimal implementation of class that
    is compatible with the `Location` type.

    Attributes:
        latitude: The latitude of an object from -90 to 90 degrees.
        longitude: The longitude of an object from -180 to 180 degrees.

    Examples:
        >>> from pysmo import MiniLocation, Location
        >>> my_location = MiniLocation(latitude=41.8781, longitude=-87.6298)
        >>> isinstance(my_location, Location)
        True
    """

    latitude: float
    longitude: float


@dataclass(kw_only=True)
class MiniStation(MiniLocation):
    """Minimal class for seismic stations.

    The `MiniStation` class provides a minimal implementation of class that
    is compatible with the `Station` type. The class is a subclass of
    `MiniLocation`, and therefore also matches the `Location` type.

    Attributes:
        name: Station name.
        network: Network name.
        elevation: Station elevation.
        longitude (float): Station longitude.
        latitude (float): Station latitude.

    Examples:
        >>> from pysmo import MiniStation, Station, Location
        >>> my_station = MiniStation(latitude=-21.680301, longitude=-46.732601,
                                     name="CACB", network="BL")
        >>> isinstance(my_station, Station)
        True
        >>> isinstance(my_station, Location)
        True
    """
    name: str
    network: str
    elevation: Optional[float] = None


@dataclass(kw_only=True)
class MiniHypocenter(MiniLocation):
    """Minimal class for hypocententers.

    The `MiniHypocenter` class provides a minimal implementation of class that
    is compatible with the `Hypocenter` type. The class is a subclass of
    `MiniLocation`, and therefore also matches the `Location` type.

    Attributes:
        depth: Hypocenter depth.
        longitude (float): Station longitude.
        latitude (float): Station latitude.

    Examples:
        >>> from pysmo import MiniHypocenter, Hypocenter, Location
        >>> my_hypo = MiniHypocenter(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(my_hypo, Hypocenter)
        True
        >>> isinstance(my_hypo, Location)
        True
    """

    depth: float
