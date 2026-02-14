from season_seismogram import Season
from pysmo import Seismogram
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np


@dataclass
class SeasonSeismogram(Seismogram):  # (1)!
    begin_time: datetime
    delta: timedelta = timedelta(seconds=0.01)
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    season: Season = Season.SUMMER
