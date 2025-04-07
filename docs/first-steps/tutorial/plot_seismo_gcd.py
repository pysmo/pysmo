from matplotlib import pyplot as plt
import numpy as np
from pysmo import Seismogram, Location
from calc_gcd_pysmo import calc_gcd


def plot_seismo_gcd(seismogram: Seismogram, point1: Location, point2: Location) -> None:
    distance = calc_gcd(point1, point2)
    t = np.array(
        [seismogram.begin_time + seismogram.delta * i for i in range(len(seismogram))]
    )
    plt.plot(t, seismogram.data, "g")
    plt.title(f"Distance: {distance} km")
    plt.gcf().autofmt_xdate()
