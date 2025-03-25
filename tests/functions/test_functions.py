from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
from datetime import timedelta
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
            (new_begin_time - seismogram.begin_time) / seismogram.delta
        )
        new_end_index = (
            ceil((new_end_time - seismogram.begin_time) / seismogram.delta) + 1
        )
        with pytest.raises(ValueError):
            _ = crop(seismogram, bad_new_begin_time, new_end_time)
        with pytest.raises(ValueError):
            _ = crop(seismogram, new_begin_time, bad_new_end_time)
        with pytest.raises(ValueError):
            _ = crop(seismogram, new_end_time, new_begin_time)
        cropped_seis = crop(seismogram, new_begin_time, new_end_time)
        assert cropped_seis.begin_time.timestamp() == pytest.approx(
            new_begin_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert cropped_seis.end_time.timestamp() == pytest.approx(
            new_end_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert all(seismogram.data[new_start_index:new_end_index] == cropped_seis.data)
