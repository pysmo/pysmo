from dataclasses import dataclass
import numpy as np


@dataclass
class TutorialSeismogram:
    event_latitude: float | None
    event_longitude: float | None
    station_latitude: float | None
    station_longitude: float | None
    delta: float
    data: np.ndarray
