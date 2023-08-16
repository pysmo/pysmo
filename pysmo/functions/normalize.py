import copy
from pysmo import Seismogram
import numpy as np


def normalize(seismogram: Seismogram) -> Seismogram:
    """
    Normalize the seismogram with its absolute max value

    :param seismogram: Seismogram object.
    :type seismogram: pysmo.Seismogram
    :returns: Normalized seismogram.
    :rtype: pysmo.Seismogram

    Example usage::
        >>> import numpy as np
        >>> from pysmo import SAC, detrend
        >>> original_seis = SAC.from_file('sacfile.sac').Seismogram
        >>> normalized_seis = normalize(original_seis)
        >>> assert np.max(normalized_seis.data) <= 1
        True
    """
    seis = copy.deepcopy(seismogram)
    norm = np.max(np.abs(seis.data))
    seis.data /= norm

    return seis
