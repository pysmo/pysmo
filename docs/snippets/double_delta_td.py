from pysmo import Seismogram
from datetime import timedelta


def double_delta_td(seismogram: Seismogram) -> timedelta:
    """Return double the sampling interval of a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        sampling interval multiplied by 2.
    """

    return seismogram.delta * 2
