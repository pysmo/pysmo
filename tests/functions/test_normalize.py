from pysmo import Seismogram
from pysmo.functions import normalize
import numpy as np


def test_normalize(seismograms: tuple[Seismogram, ...]) -> None:
    """Normalize data with its absolute maximum value"""
    for seis in seismograms:
        normalized_seis = normalize(seis)
        assert np.max(normalized_seis.data) <= 1
