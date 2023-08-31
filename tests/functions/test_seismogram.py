from pysmo import Seismogram
import pytest
import numpy as np
import matplotlib  # type: ignore

matplotlib.use('Agg')


@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir='../baseline/')
def test_plotseis(seismograms: tuple[Seismogram, ...]):  # type: ignore
    from pysmo import plotseis
    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


class TestSeismogramFunctions:

    def test_clone_to_miniseismogram(self, seismograms: tuple[Seismogram, ...]) -> None:
        """Test for cloning to MiniSeismogram object."""
        from pysmo import clone_to_miniseismogram
        for seis in seismograms:
            cloned = clone_to_miniseismogram(seis, skip_data=True)
            assert list(cloned.data) == []
            cloned = clone_to_miniseismogram(seis)
            assert all(cloned.data == seis.data)
            assert cloned.data is not seis.data
            assert cloned.begin_time == seis.begin_time
            assert cloned.begin_time is not seis.begin_time
            assert cloned.sampling_rate == seis.sampling_rate

    def test_normalize(self, seismograms: tuple[Seismogram, ...]) -> None:
        """Normalize data with its absolute maximum value"""
        from pysmo import normalize
        for seis in seismograms:
            normalized_seis = normalize(seis)
            assert np.max(normalized_seis.data) <= 1

    def test_detrend(self, seismograms: tuple[Seismogram, ...]) -> None:
        """Detrend Seismogram object and verify mean is 0."""
        from pysmo import detrend
        for seis in seismograms:
            detrended_seis = detrend(seis)
            assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0

    def test_resample(self, seismograms: tuple[Seismogram, ...]) -> None:
        """Resample Seismogram object and verify resampled data."""
        from pysmo import resample
        for seis in seismograms:
            new_sampling_rate = seis.sampling_rate * 2
            resampled_seis = resample(seis, new_sampling_rate)
            assert pytest.approx(resampled_seis.sampling_rate) == seis.sampling_rate * 2
            assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634
