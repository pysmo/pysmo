from noise_seismogram import NoiseSeismogram
import scipy


def check_for_earthquakes(seismogram: NoiseSeismogram) -> None:
    if seismogram.contains_earthquake is True:
        print("Seismogram contains an earthquake.")
    else:  # (1)!
        print("Seismogram does not contain an earthquake.")


def detrend(seismogram: NoiseSeismogram) -> None:
    seismogram.data = scipy.signal.detrend(seismogram.data)
