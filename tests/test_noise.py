"""
Run tests for pysmo.tools.noise
"""

import numpy as np
import pytest

from pysmo.tools import noise


@pytest.mark.parametrize("generator", [noise.genNoiseNLNM, noise.genNoiseNHNM])
@pytest.mark.parametrize("velocity", [False, True])
def test_gen_noise(generator, velocity):
    """Generated noise has the requested length and finite values."""
    npts = 5000
    delta = 0.05
    signal = generator(delta, npts, velocity=velocity)
    assert len(signal) == npts
    assert np.all(np.isfinite(signal))
    assert pytest.approx(np.mean(signal), abs=1e-6) == 0
