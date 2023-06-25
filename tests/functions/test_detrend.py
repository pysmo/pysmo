from pysmo import Seismogram
from pysmo.functions import detrend
import pytest
import numpy as np


def test_detrend(seismograms: tuple[Seismogram, ...]) -> None:
    """Detrend Seismogram object and verify mean is 0."""
    for seis in seismograms:
        detrended_seis = detrend(seis)
        assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0
