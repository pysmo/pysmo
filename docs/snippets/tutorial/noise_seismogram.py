from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass  # (1)!
class NoiseSeismogram:
    begin_time: pd.Timestamp  # (2)!
    delta: pd.Timedelta = pd.Timedelta(seconds=0.01)  # (3)!
    data: np.ndarray = field(default_factory=lambda: np.array([]))  # (4)!

    @property
    def end_time(self) -> pd.Timestamp:  # (5)!
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)

    contains_earthquake: bool = False  # (6)!
