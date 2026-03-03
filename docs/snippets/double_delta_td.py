from pysmo import Seismogram
import pandas as pd


def double_delta_td(seismogram: Seismogram) -> pd.Timedelta:
    """Return double the sampling interval of a seismogram.

    Args:
        seismogram: Seismogram object.

    Returns:
        sampling interval multiplied by 2.
    """

    return seismogram.delta * 2
