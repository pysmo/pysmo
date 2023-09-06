"""
Pysmo includes minimal implementations of a class for each type. They serve as
reference classes to be used with the corresponding types, and where applicable,
are used as output objects in functions.

The classes are all named using the pattern `Mini<Type>`. Thus the
[`Seismogram`][pysmo.types.Seismogram] type has a corresponding
[`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] class.
"""
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.lib.functions import (
    _normalize,
    _detrend,
    _resample
)
from datetime import datetime, timedelta
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict, Field
import numpy as np


@dataclass(kw_only=True, config=ConfigDict(arbitrary_types_allowed=True))
class MiniSeismogram:
    """Minimal class for seismogram data.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.types.Seismogram] type.

    Attributes:
        begin_time: Seismogram begin time.
        end_time: Seismogram end time.
        sampling_rate: Seismogram sampling rate.
        data: Seismogram data.
        id: Optional identifier

    Examples:
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime, timezone
        >>> import numpy as np
        >>> now = datetime.now(timezone.utc)
        >>> my_seismogram = MiniSeismogram(begin_time=now, sampling_rate=0.1,
                                           data=np.random.rand(100), id='myseis')
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = Field(default=SEISMOGRAM_DEFAULTS.begin_time)
    sampling_rate: float = Field(default=SEISMOGRAM_DEFAULTS.sampling_rate)
    data: np.ndarray = Field(default_factory=lambda: np.array([]))
    id: str | None = None

    def __len__(self) -> int:
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        if len(self) == 0:
            return self.begin_time
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


@dataclass(kw_only=True, config=ConfigDict(validate_assignment=True))
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
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(gt=-180, le=180)


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
    name: str = Field(default='')
    network: str | None = Field(default=None)
    elevation: float | None = Field(default=None)


@dataclass(kw_only=True)
class MiniHypocenter(MiniLocation):
    """Minimal class for hypocententers.

    The `MiniHypocenter` class provides a minimal implementation of class that
    is compatible with the [`Hypocenter`][pysmo.types.Hypocenter] type. The
    class is a subclass of [`MiniLocation`][pysmo.classes.mini.MiniLocation],
    and therefore also matches the [`Location`][pysmo.types.Location] type.

    Attributes:
        depth: Hypocenter depth.
        longitude (float): Event longitude.
        latitude (float): Event latitude.

    Examples:
        >>> from pysmo import MiniHypocenter, Hypocenter, Location
        >>> my_hypo = MiniHypocenter(latitude=-24.68, longitude=-26.73, depth=15234.0)
        >>> isinstance(my_hypo, Hypocenter)
        True
        >>> isinstance(my_hypo, Location)
        True
    """
    depth: float


@dataclass(kw_only=True)
class MiniEvent(MiniHypocenter):
    """Minimal class for events.

    The `MiniEvent` class provides a minimal implementation of class that is
    compatible with the [`Event`][pysmo.types.Event] type. The class is a
    subclass of [`MiniHypocenter`][pysmo.classes.mini.MiniHypocenter], and
    therefore also matches the [`Location`][pysmo.types.Location] and
    [`Hypocenter`][pysmo.types.Hypocenter] types.

    Attributes:
        depth (float): Hypocenter depth.
        longitude (float): Event longitude.
        latitude (float): Event latitude.
        time: Event origin time.

    Examples:
        >>> from pysmo import MiniEvent, Event, Hypocenter, Location
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> my_event = MiniEvent(latitude=-24.68, longitude=-26.73,
                                 depth=15234.0, time=now)
        >>> isinstance(my_event, Event)
        True
        >>> isinstance(my_event, Hypocenter)
        True
        >>> isinstance(my_event, Location)
        True
    """
    time: datetime
