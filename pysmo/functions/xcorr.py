from pysmo import Seismogram
import numpy as np


def xcorr(seis1: Seismogram, seis2: Seismogram, lagsamp: int, normalize: bool = True) -> np.ndarray:
    a, v = seis1.data, seis2.data

    if len(a) >= len(v):
        v2 = v[lagsamp:len(v)-lagsamp] if len(a) == len(v) else v
        autov = np.dot(v2, v2)
        xc = np.correlate(a, v2, mode='valid')
    else:
        autov = np.dot(v, v)
        xc = np.correlate(v, a, mode='valid')[::-1]

    if not normalize:
        autov = 1

    return xc/autov
