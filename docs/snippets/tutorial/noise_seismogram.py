from dataclasses import dataclass, field
from pandas import Timestamp, Timedelta
import numpy as np


@dataclass  # (1)!
class NoiseSeismogram:
    begin_time: Timestamp  # (2)!
    delta: Timedelta = Timedelta(seconds=0.01)  # (3)!
    data: np.ndarray = field(default_factory=lambda: np.array([]))  # (4)!

    @property
    def end_time(self) -> Timestamp:  # (5)!
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)

    contains_earthquake: bool = False  # (6)!
