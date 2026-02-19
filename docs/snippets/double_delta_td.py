from pysmo import Seismogram
from pandas import Timedelta


def double_delta_td(seismogram: Seismogram) -> Timedelta:
    """Return double the sampling interval of a seismogram.

    Args:
        seismogram: Seismogram object.

    Returns:
        sampling interval multiplied by 2.
    """

    return seismogram.delta * 2
