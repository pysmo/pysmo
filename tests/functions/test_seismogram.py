from pysmo import Seismogram
from pysmo.functions._seismogram import _WindowType
from pysmo.tools.plotutils import time_array
from pandas import Timedelta
from copy import deepcopy
from pytest_cases import parametrize_with_cases
from matplotlib.figure import Figure
from beartype.roar import BeartypeCallHintParamViolation
from tests.test_helpers import assert_seismogram_modification
from syrupy.assertion import SnapshotAssertion
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytest
import numpy as np


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_time2index(seismogram: Seismogram) -> None:
    from pysmo.functions import time2index

    assert time2index(seismogram, seismogram.begin_time) == 0
    assert time2index(seismogram, seismogram.end_time) + 1 == len(seismogram)

    time = seismogram.begin_time + 10.1 * seismogram.delta
    assert time2index(seismogram, time) == 10

    time = seismogram.begin_time + 10.8 * seismogram.delta
    assert time2index(seismogram, time) == 11

    time = seismogram.begin_time - 10.8 * seismogram.delta
    assert time2index(seismogram, time, allow_out_of_bounds=True) == -11

    with pytest.raises(ValueError):
        time2index(seismogram, seismogram.begin_time - Timedelta(seconds=1))
    with pytest.raises(ValueError):
        time2index(seismogram, seismogram.end_time + Timedelta(seconds=1))


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_normalize(seismogram: Seismogram) -> None:
    """Normalize data with its absolute maximum value"""
    from pysmo.functions import normalize

    def check_normalized(seis: Seismogram) -> None:
        assert np.max(np.abs(seis.data)) <= 1

    normalized_seis = assert_seismogram_modification(
        seismogram, normalize, custom_assertions=check_normalized
    )

    normalized_seis.data[:10] += 3
    normalized_seis.data[-10:] += 3
    normalized_seis2 = normalize(
        normalized_seis,
        clone=True,
        t1=normalized_seis.begin_time + 10 * normalized_seis.delta,
        t2=normalized_seis.end_time - 10 * normalized_seis.delta,
    )
    assert all(normalized_seis.data == normalized_seis2.data)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_normalize_snapshot(
    seismogram: Seismogram, snapshot: SnapshotAssertion
) -> None:
    """Test normalize output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the normalize function output remains
    consistent across code changes.
    """
    from pysmo.functions import normalize

    assert_seismogram_modification(seismogram, normalize, expected_data=snapshot)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_pad(seismogram: Seismogram) -> None:
    from pysmo.functions import pad

    def check_no_pad(seis: Seismogram) -> None:
        assert all(seis.data == seismogram.data)

    assert_seismogram_modification(
        seismogram,
        pad,
        seismogram.begin_time,
        seismogram.end_time,
        custom_assertions=check_no_pad,
    )

    new_begin_time = seismogram.begin_time - seismogram.delta * 10
    new_end_time = seismogram.end_time + seismogram.delta * 10

    def check_padded(seis: Seismogram) -> None:
        assert (
            pytest.approx(seis.begin_time.timestamp())
            == (seismogram.begin_time - seismogram.delta * 10).timestamp()
        )
        assert (
            pytest.approx(seis.end_time.timestamp())
            == (seismogram.end_time + seismogram.delta * 10).timestamp()
        )
        assert seis.data[:10].sum() == 0
        assert seis.data[-10:].sum() == 0
        np.testing.assert_array_equal(seis.data[10:-10], seismogram.data)

    assert_seismogram_modification(
        seismogram,
        pad,
        new_begin_time,
        new_end_time,
        custom_assertions=check_padded,
    )

    with pytest.raises(ValueError):
        pad(
            seismogram,
            seismogram.begin_time,
            seismogram.begin_time - Timedelta(seconds=1),
        )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_pad_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test pad output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the pad function output remains
    consistent across code changes. Tests padding with specific begin/end times.
    """
    from pysmo.functions import pad

    new_begin_time = seismogram.begin_time - seismogram.delta * 3.5
    new_end_time = seismogram.end_time + seismogram.delta * 3.5

    assert_seismogram_modification(
        seismogram, pad, new_begin_time, new_end_time, expected_data=snapshot
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_detrend(seismogram: Seismogram) -> None:
    """Detrend Seismogram object and verify mean is 0."""
    from pysmo.functions import detrend

    def check_detrended(seis: Seismogram) -> None:
        assert pytest.approx(np.mean(seis.data), abs=1e-6) == 0

    assert_seismogram_modification(
        seismogram, detrend, custom_assertions=check_detrended
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_detrend_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test detrend output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the detrend function output remains
    consistent across code changes.
    """
    from pysmo.functions import detrend

    assert_seismogram_modification(seismogram, detrend, expected_data=snapshot)


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_resample(seismogram: Seismogram) -> None:
    """Resample Seismogram object and verify resampled data."""
    from pysmo.functions import resample

    def check_unchanged(seis: Seismogram) -> None:
        np.testing.assert_array_equal(seis.data, seismogram.data)

    assert_seismogram_modification(
        seismogram, resample, seismogram.delta, custom_assertions=check_unchanged
    )

    new_delta = seismogram.delta * 2

    def check_resampled(seis: Seismogram) -> None:
        assert (
            pytest.approx(seis.delta.total_seconds(), abs=1e-4)
            == seismogram.delta.total_seconds() * 2
        )
        # Verify resampled data has finite values
        assert np.all(np.isfinite(seis.data)), "Resampled data should be finite"
        # Verify resampling reduced the number of samples approximately by factor of 2
        expected_length = len(seismogram) // 2
        assert (
            abs(len(seis) - expected_length) <= 2
        ), "Length should be approximately halved"

    assert_seismogram_modification(
        seismogram, resample, new_delta, custom_assertions=check_resampled
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_resample_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test resample output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the resample function output remains
    consistent across code changes. Tests resampling with doubled delta.
    """
    from pysmo.functions import resample

    new_delta = seismogram.delta * 2

    assert_seismogram_modification(
        seismogram, resample, new_delta, expected_data=snapshot
    )


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_crop(seismogram: Seismogram) -> None:
    """Crop Seismogram object and verify cropped data."""
    from pysmo.functions import crop

    def check_no_crop(seis: Seismogram) -> None:
        assert len(seis) == len(seismogram)
        assert seis.begin_time.timestamp() == pytest.approx(
            seismogram.begin_time.timestamp()
        )
        assert seis.end_time.timestamp() == pytest.approx(
            seismogram.end_time.timestamp()
        )

    assert_seismogram_modification(
        seismogram,
        crop,
        begin_time=seismogram.begin_time,
        end_time=seismogram.end_time,
        custom_assertions=check_no_crop,
    )

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
    new_start_index = round((new_begin_time - seismogram.begin_time) / seismogram.delta)
    new_end_index = round((new_end_time - seismogram.begin_time) / seismogram.delta) + 1
    with pytest.raises(ValueError):
        crop(seismogram, bad_new_begin_time, new_end_time)
    with pytest.raises(ValueError):
        crop(seismogram, new_begin_time, bad_new_end_time)
    with pytest.raises(ValueError):
        crop(seismogram, new_end_time, new_begin_time)

    def check_cropped(seis: Seismogram) -> None:
        assert seis.begin_time.timestamp() == pytest.approx(
            new_begin_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert seis.end_time.timestamp() == pytest.approx(
            new_end_time.timestamp(), abs=seismogram.delta.total_seconds()
        )
        assert all(seismogram.data[new_start_index:new_end_index] == seis.data)

    assert_seismogram_modification(
        seismogram,
        crop,
        new_begin_time,
        new_end_time,
        custom_assertions=check_cropped,
    )

    if len(seismogram) > 100:
        seis3 = deepcopy(seismogram)
        seis3.data = seis3.data[:100]
        new_begin_time = seis3.begin_time + seis3.delta
        new_end_time = seis3.end_time - seis3.delta
        cropped_seis = crop(seis3, new_begin_time, new_end_time, clone=True)
        assert all(cropped_seis.data == seis3.data[1:-1])


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
def test_crop_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test crop output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the crop function output remains
    consistent across code changes. Tests cropping to middle half of data.
    """
    from pysmo.functions import crop

    new_begin_time = (
        seismogram.begin_time + (seismogram.end_time - seismogram.begin_time) / 4
    )
    new_end_time = (
        seismogram.end_time - (seismogram.end_time - seismogram.begin_time) / 4
    )

    assert_seismogram_modification(
        seismogram, crop, new_begin_time, new_end_time, expected_data=snapshot
    )


class TestTaper:
    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    @pytest.mark.mpl_image_compare(remove_text=True)
    def test_taper(self, seismogram: Seismogram) -> Figure:
        from pysmo.functions import taper

        seismogram.data = np.ones(len(seismogram))

        with pytest.raises(BeartypeCallHintParamViolation):
            _ = taper(seismogram, "abc", clone=True)  # type: ignore
        with pytest.raises(BeartypeCallHintParamViolation):
            _ = taper(seismogram, 1.7, clone=True)
        fig = plt.figure()
        time = time_array(seismogram)
        plt.plot(time, seismogram.data, scalex=True, scaley=True)
        plt.plot(time, seismogram.data, scalex=True, scaley=True)
        methods: list[_WindowType] = [
            "barthann",
            "bartlett",
            "blackman",
            "blackmanharris",
            "bohman",
            "cosine",
            ("general_hamming", 0.52),
            ("general_hamming", 0.75),
        ]
        for method in methods:
            seis_taper = taper(seismogram, 0.5, method, clone=True)
            plt.plot(time, seis_taper.data, scalex=True, scaley=True)
            seis_taper = taper(
                seismogram,
                (seismogram.end_time - seismogram.begin_time) * 0.5,
                method,
                clone=True,
            )
            plt.plot(time, seis_taper.data, scalex=True, scaley=True)
        plt.xlabel("Time")
        plt.gcf().autofmt_xdate()
        fmt = mdates.DateFormatter("%H:%M:%S")
        plt.gca().xaxis.set_major_formatter(fmt)
        return fig


class TestWindow:
    TAPER_WIDTH: Timedelta | float = Timedelta(seconds=500)

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_window(self, seismogram: Seismogram) -> None:
        from pysmo.functions import window, time2index

        taper_width = self.TAPER_WIDTH

        window_begin_time = seismogram.begin_time + Timedelta(seconds=600)
        window_end_time = window_begin_time + Timedelta(seconds=1000)
        windowed_seis = window(
            seismogram,
            window_begin_time,
            window_end_time,
            taper_width,
            same_shape=True,
            clone=True,
        )
        assert windowed_seis.begin_time.timestamp() == pytest.approx(
            seismogram.begin_time.timestamp()
        )
        assert windowed_seis.end_time.timestamp() == pytest.approx(
            seismogram.end_time.timestamp()
        )

        if isinstance(taper_width, Timedelta):
            taper_start = window_begin_time - taper_width
            taper_end = window_end_time + taper_width
        else:
            taper_start = (
                window_begin_time - (window_end_time - window_begin_time) * taper_width
            )
            taper_end = (
                window_end_time + (window_end_time - window_begin_time) * taper_width
            )

        taper_start_index = time2index(seismogram, taper_start)
        assert np.max(np.abs(windowed_seis.data[:taper_start_index])) < 1e-6
        taper_end_index = time2index(seismogram, taper_end)
        assert np.max(np.abs(windowed_seis.data[taper_end_index:])) < 1e-6

        window(
            seismogram, window_begin_time, window_end_time, taper_width, same_shape=True
        )
        assert all(windowed_seis.data == seismogram.data)


class TestWindowFloat(TestWindow):
    TAPER_WIDTH: Timedelta | float = 0.1
