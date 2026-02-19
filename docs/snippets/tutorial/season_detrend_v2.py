from season_seismogram import SeasonSeismogram, Season
from functions_v3 import detrend
from pandas import Timestamp
import numpy as np


def main() -> None:
    # Create a sample SeasonSeismogram instance with random data
    begin_time = Timestamp(2023, 1, 1, 0, 0, 0)
    data = np.random.randn(1000)
    season_seismogram = SeasonSeismogram(
        begin_time=begin_time, data=data, season=Season.WINTER
    )

    # Use the season_seismogram with the detrend function
    detrend(season_seismogram)


if __name__ == "__main__":
    main()
