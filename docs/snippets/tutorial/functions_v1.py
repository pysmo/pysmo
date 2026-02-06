from noise_seismogram import NoiseSeismogram
import scipy


def check_for_earthquakes(seismogram: NoiseSeismogram) -> None:
    if seismogram.contains_earthquake is True:
        print("Seismogram contains an earthquake.")
    elif seismogram.contains_earthquake is False:
        print("Seismogram does not contain an earthquake.")
    else:
        print("Seismogram earthquake status is unknown.")


def detrend(seismogram: NoiseSeismogram) -> None:
    seismogram.data = scipy.signal.detrend(seismogram.data)
