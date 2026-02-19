from season_seismogram import Season
from pysmo import Seismogram
from dataclasses import dataclass, field
from pandas import Timestamp, Timedelta
import numpy as np


@dataclass
class SeasonSeismogram(Seismogram):  # (1)!
    begin_time: Timestamp
    delta: Timedelta = Timedelta(seconds=0.01)
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    season: Season = Season.SUMMER
