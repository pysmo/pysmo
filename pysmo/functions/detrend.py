import scipy.signal  # type: ignore
import copy
from pysmo import Seismogram


def detrend(seismogram: Seismogram) -> Seismogram:
    """
    Remove linear and/or constant trends from SAC object data.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Detrended seismogram.

    Examples:
        >>> import numpy as np
        >>> from pysmo import SAC, detrend
        >>> original_seis = SAC.from_file('sacfile.sac').seismogram
        >>> detrended_seis = detrend(original_seis)
        >>> assert np.mean(detrended_seis.data) == 0
        True
    """
    seis = copy.deepcopy(seismogram)
    seis.data = scipy.signal.detrend(seismogram.data)
    return seis
