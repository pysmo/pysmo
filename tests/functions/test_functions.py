from pysmo import Seismogram, Location, SAC, MiniSeismogram
import pytest
import pytest_cases
import numpy as np
import matplotlib  # type: ignore
from tests.conftest import TESTDATA

matplotlib.use("Agg")


SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    sampling_rate=SACSEIS.sampling_rate,
    data=SACSEIS.data,
)


@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir="../baseline/")
def test_plotseis(seismograms: tuple[Seismogram, ...]):  # type: ignore
    from pysmo import plotseis

    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
class TestSeismogramFunctions:
    def test_normalize(self, seismogram: Seismogram) -> None:
        """Normalize data with its absolute maximum value"""
        from pysmo import normalize

        normalized_seis = normalize(seismogram)
        assert np.max(normalized_seis.data) <= 1

    def test_detrend(self, seismogram: Seismogram) -> None:
        """Detrend Seismogram object and verify mean is 0."""
        from pysmo import detrend

        detrended_seis = detrend(seismogram)
        assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0

    def test_resample(self, seismogram: Seismogram) -> None:
        """Resample Seismogram object and verify resampled data."""
        from pysmo import resample

        new_sampling_rate = seismogram.sampling_rate * 2
        resampled_seis = resample(seismogram, new_sampling_rate)
        assert (
            pytest.approx(resampled_seis.sampling_rate) == seismogram.sampling_rate * 2
        )
        assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634


def test_azimuth(
    stations: tuple[Location, ...], hypocenters: tuple[Location, ...]
) -> None:
    """Calculate azimuth from Event and Station objects"""
    from pysmo import azimuth, backazimuth, distance

    for location1 in hypocenters:
        for location2 in stations:
            azimuth_wgs84 = azimuth(location1, location2)
            azimuth_switched_wgs84 = azimuth(location2, location1)
            azimuth_clrk66 = azimuth(location1, location2, ellps="clrk66")
            assert pytest.approx(azimuth_wgs84) == 181.9199258637492
            assert pytest.approx(azimuth_switched_wgs84) == 2.4677533885335947
            assert pytest.approx(azimuth_clrk66) == 181.92001941872516

            backazimuth_wgs84 = backazimuth(location1, location2)
            backazimuth_switched_wgs84 = backazimuth(location2, location1)
            backazimuth_clrk66 = backazimuth(location1, location2, ellps="clrk66")
            assert pytest.approx(backazimuth_wgs84) == 2.4677533885335947
            assert pytest.approx(backazimuth_switched_wgs84) == 181.9199258637492
            assert pytest.approx(backazimuth_clrk66) == 2.467847115319614

            distance_wgs84 = distance(location1, location2)
            distance_clrk66 = distance(location1, location2, ellps="clrk66")
            assert pytest.approx(distance_wgs84) == 1889154.9940066523
            assert pytest.approx(distance_clrk66) == 1889121.7781364019
