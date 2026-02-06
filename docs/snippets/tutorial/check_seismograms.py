from pysmo import Seismogram
from noise_seismogram import NoiseSeismogram
from season_seismogram import SeasonSeismogram
from datetime import datetime
import numpy as np


def main() -> None:
    begin_time = datetime(2023, 1, 1, 0, 0, 0)
    data = np.random.randn(1000)
    noise_seismogram = NoiseSeismogram(begin_time=begin_time, data=data)
    season_seismogram = SeasonSeismogram(begin_time=begin_time, data=data)

    print(
        f"noise_seismogram is a Seismogram instance: {isinstance(noise_seismogram, Seismogram)}"
    )
    print(
        f"season_seismogram is a Seismogram instance: {isinstance(season_seismogram, Seismogram)}"
    )


if __name__ == "__main__":
    main()
