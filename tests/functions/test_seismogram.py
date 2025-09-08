from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
from datetime import timedelta
from copy import deepcopy
from numpy.testing import assert_array_equal
import pytest
import pytest_cases
import numpy as np
from tests.conftest import TESTDATA


SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
class TestSeismogramFunctions:
    def test_time2index(self, seismogram: Seismogram) -> None:
        from pysmo.functions import time2index

        assert time2index(seismogram, seismogram.begin_time) == 0
        assert time2index(seismogram, seismogram.end_time) + 1 == len(seismogram)

        time = seismogram.begin_time + 10.1 * seismogram.delta
        assert time2index(seismogram, time) == 10
        assert time2index(seismogram, time, method="ceil") == 11
        assert time2index(seismogram, time, method="floor") == 10

        time = seismogram.begin_time + 10.8 * seismogram.delta
        assert time2index(seismogram, time) == 11
        assert time2index(seismogram, time, method="ceil") == 11
        assert time2index(seismogram, time, method="floor") == 10

        with pytest.raises(ValueError):
            time2index(seismogram, seismogram.begin_time - timedelta(seconds=1))
        with pytest.raises(ValueError):
            time2index(seismogram, seismogram.end_time + timedelta(seconds=1))
        with pytest.raises(ValueError):
            time2index(
                seismogram,
                seismogram.end_time - timedelta(seconds=1),
                method="not a method",  # type: ignore
            )

    def test_normalize(self, seismogram: Seismogram) -> None:
        """Normalize data with its absolute maximum value"""
        from pysmo.functions import normalize

        normalized_seis = normalize(seismogram, clone=True)
        assert np.max(normalized_seis.data) <= 1

        seis2 = deepcopy(seismogram)
        normalize(seis2)
        assert all(normalized_seis.data == seis2.data)

        normalized_seis.data[:10] += 3
        normalized_seis.data[-10:] += 3
        normalized_seis2 = normalize(
            normalized_seis,
            clone=True,
            t1=normalized_seis.begin_time + 10 * normalized_seis.delta,
            t2=normalized_seis.end_time - 10 * normalized_seis.delta,
        )
        assert all(normalized_seis.data == normalized_seis2.data)

    def test_detrend(self, seismogram: Seismogram) -> None:
        """Detrend Seismogram object and verify mean is 0."""
        from pysmo.functions import detrend

        detrended_seis = detrend(seismogram, clone=True)
        assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0

        seis2 = deepcopy(seismogram)
        detrend(seis2)
        assert all(detrended_seis.data == seis2.data)

    def test_resample(self, seismogram: Seismogram) -> None:
        """Resample Seismogram object and verify resampled data."""
        from pysmo.functions import resample

        new_delta = seismogram.delta * 2
        resampled_seis = resample(seismogram, new_delta, clone=True)
        assert pytest.approx(resampled_seis.delta) == seismogram.delta * 2
        assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634

        seis2 = deepcopy(seismogram)
        resample(seis2, new_delta)
        assert all(resampled_seis.data == seis2.data)

    def test_crop(self, seismogram: Seismogram) -> None:
        """Crop Seismogram object and verify cropped data."""
        from pysmo.functions import crop

        cropped_seis = crop(
            seismogram,
            begin_time=seismogram.begin_time,
            end_time=seismogram.end_time,
            clone=True,
        )
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
        new_start_index = round(
            (new_begin_time - seismogram.begin_time) / seismogram.delta
        )
        new_end_index = (
            round((new_end_time - seismogram.begin_time) / seismogram.delta) + 1
        )
        with pytest.raises(ValueError):
            crop(seismogram, bad_new_begin_time, new_end_time)
        with pytest.raises(ValueError):
            crop(seismogram, new_begin_time, bad_new_end_time)
        with pytest.raises(ValueError):
            crop(seismogram, new_end_time, new_begin_time)
        cropped_seis = crop(seismogram, new_begin_time, new_end_time, clone=True)
        assert cropped_seis.begin_time.timestamp() == pytest.approx(
            new_begin_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert cropped_seis.end_time.timestamp() == pytest.approx(
            new_end_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert all(seismogram.data[new_start_index:new_end_index] == cropped_seis.data)

        seis2 = deepcopy(seismogram)
        crop(seis2, new_begin_time, new_end_time)
        assert all(cropped_seis.data == seis2.data)

        if len(seismogram) > 100:
            seis3 = deepcopy(seismogram)
            seis3.data = seis3.data[:100]
            new_begin_time = seis3.begin_time + seis3.delta
            new_end_time = seis3.end_time - seis3.delta
            cropped_seis = crop(seis3, new_begin_time, new_end_time, clone=True)
            assert all(cropped_seis.data == seis3.data[1:-1])

    @pytest.mark.mpl_image_compare(remove_text=True)
    def test_taper(self, seismogram: Seismogram):  # type: ignore
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from pysmo.tools.plotutils import time_array
        from pysmo.functions import taper
        from typing import get_args, Literal

        seismogram.data = np.ones(len(seismogram))

        with pytest.raises(TypeError):
            _ = taper(seismogram, "abc", clone=True)  # type: ignore
        with pytest.raises(ValueError):
            _ = taper(seismogram, 0.7, clone=True)
        fig = plt.figure()
        time = time_array(seismogram)
        plt.plot(time, seismogram.data, scalex=True, scaley=True)
        plt.plot(time, seismogram.data, scalex=True, scaley=True)
        for method in get_args(
            Literal["bartlett", "blackman", "hamming", "hanning", "kaiser"]
        ):
            seis_taper = taper(seismogram, 0.2, method, clone=True)
            plt.plot(time, seis_taper.data, scalex=True, scaley=True)
        plt.xlabel("Time")
        plt.gcf().autofmt_xdate()
        fmt = mdates.DateFormatter("%H:%M:%S")
        plt.gca().xaxis.set_major_formatter(fmt)
        seis_taper_timedelta = taper(
            seismogram, (seismogram.end_time - seismogram.begin_time) * 0.1, clone=True
        )
        taper(seismogram, 0.1)
        assert_array_equal(seismogram.data, seis_taper_timedelta.data)
        return fig
