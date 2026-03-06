import scipy
from noise_seismogram import NoiseSeismogram

from pysmo import Seismogram  # (1)!


def check_for_earthquakes(seismogram: NoiseSeismogram) -> None:
    if seismogram.contains_earthquake is True:
        print("Seismogram contains an earthquake.")
    else:
        print("Seismogram does not contain an earthquake.")


def detrend(seismogram: Seismogram) -> None:  # (2)!
    seismogram.data = scipy.signal.detrend(seismogram.data)
