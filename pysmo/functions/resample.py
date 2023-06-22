import scipy.signal  # type: ignore
import copy
from pysmo import Seismogram


def resample(seismogram: Seismogram, sampling_rate: float) -> Seismogram:
    """
    Resamples Seismogram object data using Fourier method.

    :param seismogram: Seismogram object.
    :type seismogram: pysmo.Seismogram
    :param sampling_rate: New sampling rate.
    :type sampling_rate: float
    :returns: Detrended seismogram.
    :rtype: pysmo.Seismogram

    Example usage::

        >>> from pysmo import SAC, resample
        >>> original_seis = SAC.from_file('sacfile.sac').Seismogram
        >>> len(original_seis)
        20000
        >>> original_sampling_rate = original_seis.sampling_rate
        >>> new_sampling_rate = original_sampling_rate * 2
        >>> resampled_seis = resample(original_seis, new_sampling_rate)
        >>> len(resampled_seis)
        10000
    """
    seis = copy.deepcopy(seismogram)
    len_old = len(seis)
    sampling_rate_old = seis.sampling_rate
    len_new = int(len_old * sampling_rate_old / sampling_rate)
    seis.data = scipy.signal.resample(seis.data, len_new)
    seis.sampling_rate = sampling_rate
    return seis
