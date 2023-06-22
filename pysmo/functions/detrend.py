import scipy.signal  # type: ignore
import copy
from pysmo import Seismogram


def detrend(seismogram: Seismogram) -> Seismogram:
    """
    Remove linear and/or constant trends from SAC object data.

    :param seismogram: Seismogram object.
    :type seismogram: pysmo.Seismogram
    :returns: Detrended seismogram.
    :rtype: pysmo.Seismogram

    Example usage::

        >>> import numpy as np
        >>> from pysmo import SAC, detrend
        >>> original_seis = SAC.from_file('sacfile.sac').Seismogram
        >>> detrended_seis = detrend(original_seis)
        >>> assert np.mean(detrended_seis.data) == 0
        True
    """
    seis = copy.deepcopy(seismogram)
    seis.data = scipy.signal.detrend(seismogram.data)
    return seis
