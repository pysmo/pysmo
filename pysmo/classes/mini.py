import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional


@dataclass
class MiniSeismogram():
    """Class for Seismogram data"""
    begin_time: datetime = datetime.fromtimestamp(0, tz=timezone.utc)
    sampling_rate: float = 1
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    id: Optional[str] = None

    def __len__(self) -> int:
        """Returns the length (number of points) of a seismogram."""
        return np.size(self.data)

    @property
    def end_time(self) -> datetime:
        """Returns the end time."""
        return self.begin_time + timedelta(seconds=self.sampling_rate*(len(self)-1))


@dataclass
class MiniLocation:
    """Class for geographical locations"""
    latitude: float
    longitude: float


@dataclass
class MiniStation(MiniLocation):
    """Class for seismic stations"""
    name: str
    network: str
    elevation: Optional[float] = None


@dataclass
class MiniHypocenter(MiniLocation):
    """Class for hypocenters"""
    depth: float
