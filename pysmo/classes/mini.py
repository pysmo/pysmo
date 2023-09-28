"""
Pysmo includes minimal implementations of a class for each type. They serve as
reference classes to be used with the corresponding types, and where applicable,
are used as output objects in functions. The classes are all named using the
pattern `Mini<Type>`. Thus the [`Seismogram`][pysmo.types.Seismogram] type has
a corresponding [`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] class.
"""
import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo.lib.functions import _normalize, _detrend, _resample
from pysmo import Seismogram
from datetime import datetime, timedelta
from attrs import define, field, validators, converters
from attrs_strict import type_validator
import numpy as np
import copy


@define(kw_only=True)
class MiniSeismogram:
    """Minimal class for seismogram data.

    The `MiniSeismogram` class provides a minimal implementation of class that
    is compatible with the [`Seismogram`][pysmo.types.Seismogram] type.

    Attributes:
        begin_time: Seismogram begin time.
        end_time: Seismogram end time.
        delta: Seismogram sampling interval.
        data: Seismogram data.

    Examples:
        >>> from pysmo import MiniSeismogram, Seismogram
        >>> from datetime import datetime, timezone
        >>> import numpy as np
        >>> now = datetime.now(timezone.utc)
        >>> my_seismogram = MiniSeismogram(begin_time=now, delta=0.1,
                                           data=np.random.rand(100), id='myseis')
        >>> isinstance(my_seismogram, Seismogram)
        True
    """

    begin_time: datetime = field(
        default=SEISMOGRAM_DEFAULTS.begin_time, validator=type_validator()
    )
    delta: float = field(
        default=SEISMOGRAM_DEFAULTS.delta,
        converter=float,
        validator=type_validator(),
    )
    data: np.ndarray = field(factory=lambda: np.array([]), validator=type_validator())

    def __len__(self) -> int:
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + timedelta(seconds=self.delta * (len(self) - 1))

    @classmethod
    def clone(cls, seismogram: Seismogram, skip_data: bool = False) -> Self:
        """Create a new MiniSeismogram instance from an existing
        [Seismogram][pysmo.types.Seismogram] object.

        Attributes:
            seismogram: The Seismogram to be cloned.
            skip_data: Create clone witout copying data.

        Returns:
            A copy of the original Seismogram object.

        Examples:
            Create a copy of a [SAC][pysmo.classes.sac.SAC] object without data:

            >>> from pysmo import SAC, MiniSeismogram
            >>> original_seis = SAC.from_file('testfile.sac').seismogram
            >>> cloned_seis = MiniSeismogram.clone(original_seis, skip_data=True)
            >>> print(cloned_seis.data)
            []

            Create a copy of a [SAC][pysmo.classes.sac.SAC] object with data:

            >>> from pysmo import SAC, MiniSeismogram
            >>> from numpy.testing import assert_allclose
            >>> original_seis = SAC.from_file('testfile.sac').seismogram
            >>> cloned_seis = MiniSeismogram.clone(original_seis)
            >>> assert_allclose(original_seis.data, cloned_seis.data)
            True
            >>> print(cloned_seis.data)
            [2302. 2313. 2345. ... 2836. 2772. 2723.]
        """
        cloned_seismogram = cls()
        cloned_seismogram.begin_time = copy.copy(seismogram.begin_time)
        cloned_seismogram.delta = seismogram.delta
        if not skip_data:
            cloned_seismogram.data = copy.copy(seismogram.data)
        return cloned_seismogram

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

    def resample(self, delta: float) -> None:
        """Resample Seismogram object data using the Fourier method.

        Parameters:
            delta: New sampling interval.

        Examples:
            >>> from pysmo import MiniSeismogram
            >>> my_seis = MiniSeismogram(data=np.random.rand(10000))
            >>> len(my_seis)
            10000
            >>> new_delta = my_seis.delta * 2
            >>> my_seis.resample(new_delta)
            >>> len(my_seis)
            5000
        """
        self.data, self.delta = _resample(self, delta), delta


@define(kw_only=True)
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

    latitude: float = field(
        converter=float,
        validator=[validators.ge(-90), validators.le(90), type_validator()],
    )
    longitude: float = field(
        converter=float,
        validator=[validators.gt(-180), validators.le(180), type_validator()],
    )


@define(kw_only=True)
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

    name: str = field(validator=type_validator())
    network: str | None = field(default=None, validator=type_validator())
    elevation: float | None = field(
        default=None,
        converter=converters.optional(float),
        validator=validators.optional(
            [validators.gt(-180), validators.le(180), type_validator()]
        ),
    )


@define(kw_only=True)
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

    depth: float = field(converter=float, validator=type_validator())


@define(kw_only=True)
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

    time: datetime = field(validator=type_validator())
