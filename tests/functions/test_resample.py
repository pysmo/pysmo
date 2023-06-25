from pysmo import Seismogram
from pysmo.functions import resample
import pytest


def test_resample(seismograms: tuple[Seismogram, ...]) -> None:
    """Resample Seismogram object and verify resampled data."""
    for seis in seismograms:
        new_sampling_rate = seis.sampling_rate * 2
        resampled_seis = resample(seis, new_sampling_rate)
        assert pytest.approx(resampled_seis.sampling_rate) == seis.sampling_rate * 2
        assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634
