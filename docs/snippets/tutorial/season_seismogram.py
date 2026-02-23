from dataclasses import dataclass, field
from pandas import Timestamp, Timedelta
from enum import StrEnum
import numpy as np


class Season(StrEnum):  # (1)!
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


@dataclass
class SeasonSeismogram:
    begin_time: Timestamp
    delta: Timedelta = Timedelta(seconds=0.01)
    data: np.ndarray = field(default_factory=lambda: np.array([]))

    @property
    def end_time(self) -> Timestamp:
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)

    season: Season = Season.SUMMER  # (2)!
