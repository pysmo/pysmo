from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
import numpy as np


class Season(StrEnum):  # (1)!
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


@dataclass
class SeasonSeismogram:
    begin_time: datetime
    delta: timedelta = timedelta(seconds=0.01)
    data: np.ndarray = field(default_factory=lambda: np.array([]))

    def __len__(self) -> int:
        return len(self.data)

    @property
    def end_time(self) -> datetime:
        if len(self) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self) - 1)

    season: Season = Season.SUMMER  # (2)!
