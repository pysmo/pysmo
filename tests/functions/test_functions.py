from pysmo import Seismogram, Location, MiniSeismogram
from pysmo.classes import SAC
import pytest
import pytest_cases
import numpy as np
import matplotlib  # type: ignore
from tests.conftest import TESTDATA

matplotlib.use("Agg")


SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir="../baseline/")
def test_plotseis(seismograms: tuple[Seismogram, ...]):  # type: ignore
    from pysmo.functions import plotseis

    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
class TestSeismogramFunctions:
    def test_normalize(self, seismogram: Seismogram) -> None:
        """Normalize data with its absolute maximum value"""
        from pysmo.functions import normalize

        normalized_seis = normalize(seismogram)
        assert np.max(normalized_seis.data) <= 1

    def test_detrend(self, seismogram: Seismogram) -> None:
        """Detrend Seismogram object and verify mean is 0."""
        from pysmo.functions import detrend

        detrended_seis = detrend(seismogram)
        assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0

    def test_resample(self, seismogram: Seismogram) -> None:
        """Resample Seismogram object and verify resampled data."""
        from pysmo.functions import resample

        new_delta = seismogram.delta * 2
        resampled_seis = resample(seismogram, new_delta)
        assert pytest.approx(resampled_seis.delta) == seismogram.delta * 2
        assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634

    def test_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.functions import time_array
        from matplotlib.dates import num2date

        times = time_array(seismogram)
        assert len(times) == len(seismogram)
        assert num2date(times[0]) == seismogram.begin_time
        assert num2date(times[-1]) == seismogram.end_time

    def test_unix_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.functions import unix_time_array
        from datetime import datetime, timezone

        unix_times = unix_time_array(seismogram)
        assert len(unix_times) == len(seismogram)
        assert (
            datetime.fromtimestamp(unix_times[0], timezone.utc) == seismogram.begin_time
        )
        assert (
            datetime.fromtimestamp(unix_times[-1], timezone.utc) == seismogram.end_time
        )

    def test_crop(self, seismogram: Seismogram) -> None:
        """Crop Seismogram object and verify cropped data."""
        from pysmo.functions import crop
        from math import floor, ceil

        cropped_seis = crop(seismogram, seismogram.begin_time, seismogram.end_time)
        assert len(cropped_seis) == len(seismogram)
        assert cropped_seis.begin_time == seismogram.begin_time
        assert cropped_seis.end_time == seismogram.end_time

        new_begin_time = (
            seismogram.begin_time + (seismogram.end_time - seismogram.begin_time) / 4
        )
        new_end_time = (
            seismogram.end_time - (seismogram.end_time - seismogram.begin_time) / 4
        )
        bad_new_begin_time = (
            seismogram.begin_time - (seismogram.end_time - seismogram.begin_time) / 4
        )
        bad_new_end_time = (
            seismogram.end_time + (seismogram.end_time - seismogram.begin_time) / 4
        )
        new_start_index = floor(
            (new_begin_time - seismogram.begin_time).total_seconds() / seismogram.delta
        )
        new_end_index = ceil(
            (new_end_time - seismogram.begin_time).total_seconds() / seismogram.delta
        )
        with pytest.raises(ValueError):
            _ = crop(seismogram, bad_new_begin_time, new_end_time)
        with pytest.raises(ValueError):
            _ = crop(seismogram, new_begin_time, bad_new_end_time)
        with pytest.raises(ValueError):
            _ = crop(seismogram, new_end_time, new_begin_time)
        cropped_seis = crop(seismogram, new_begin_time, new_end_time)
        assert cropped_seis.begin_time.timestamp() == pytest.approx(
            new_begin_time.timestamp(), abs=seismogram.delta
        )
        assert cropped_seis.end_time.timestamp() == pytest.approx(
            new_end_time.timestamp(), abs=seismogram.delta
        )
        assert all(seismogram.data[new_start_index:new_end_index] == cropped_seis.data)


def test_azimuth(
    stations: tuple[Location, ...], hypocenters: tuple[Location, ...]
) -> None:
    """Calculate azimuth from Event and Station objects"""
    from pysmo.functions import azimuth, backazimuth, distance

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
