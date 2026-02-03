from pysmo import Seismogram
from pysmo.functions._seismogram import _WindowType
from pysmo.tools.plotutils import time_array
from datetime import timedelta
from copy import deepcopy
from pytest_cases import parametrize_with_cases
from matplotlib.figure import Figure
from beartype.roar import BeartypeCallHintParamViolation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pytest
import numpy as np


@parametrize_with_cases("seismogram")
def test_time2index(seismogram: Seismogram) -> None:
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

    time = seismogram.begin_time - 10.8 * seismogram.delta
    assert time2index(seismogram, time, allow_out_of_bounds=True) == -11
    assert time2index(seismogram, time, method="ceil", allow_out_of_bounds=True) == -10
    assert time2index(seismogram, time, method="floor", allow_out_of_bounds=True) == -11

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


@parametrize_with_cases("seismogram")
def test_normalize(seismogram: Seismogram) -> None:
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


@parametrize_with_cases("seismogram")
def test_pad(seismogram: Seismogram) -> None:
    from pysmo.functions import pad

    padded_seis = pad(
        seismogram,
        seismogram.begin_time,
        seismogram.end_time,
        clone=True,
    )
    assert all(padded_seis.data == seismogram.data)
    new_begin_time = seismogram.begin_time - seismogram.delta * 3.5
    new_end_time = seismogram.end_time + seismogram.delta * 3.5
    pad_seis = pad(seismogram, new_begin_time, new_end_time, clone=True)
    assert pad_seis.begin_time == seismogram.begin_time - seismogram.delta * 4
    assert pad_seis.end_time == seismogram.end_time + seismogram.delta * 4
    assert pad_seis.data[:4].sum() == 0
    assert pad_seis.data[-4:].sum() == 0
    np.testing.assert_array_equal(pad_seis.data[4:-4], seismogram.data)
    with pytest.raises(ValueError):
        pad(
            seismogram,
            seismogram.begin_time,
            seismogram.begin_time - timedelta(seconds=1),
        )


@parametrize_with_cases("seismogram")
def test_detrend(seismogram: Seismogram) -> None:
    """Detrend Seismogram object and verify mean is 0."""
    from pysmo.functions import detrend

    detrended_seis = detrend(seismogram, clone=True)
    assert pytest.approx(np.mean(detrended_seis.data), abs=1e-6) == 0

    seis2 = deepcopy(seismogram)
    detrend(seis2)
    assert all(detrended_seis.data == seis2.data)


@parametrize_with_cases("seismogram")
def test_resample(seismogram: Seismogram) -> None:
    """Resample Seismogram object and verify resampled data."""
    from pysmo.functions import resample

    resampled_seis = resample(seismogram, seismogram.delta, clone=True)
    np.testing.assert_array_equal(resampled_seis.data, seismogram.data)

    new_delta = seismogram.delta * 2
    resampled_seis = resample(seismogram, new_delta, clone=True)
    assert pytest.approx(resampled_seis.delta) == seismogram.delta * 2
    assert pytest.approx(resampled_seis.data[6]) == 2202.0287804516634

    seis2 = deepcopy(seismogram)
    resample(seis2, new_delta)
    assert all(resampled_seis.data == seis2.data)


@parametrize_with_cases("seismogram")
def test_crop(seismogram: Seismogram) -> None:
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
    new_start_index = round((new_begin_time - seismogram.begin_time) / seismogram.delta)
    new_end_index = round((new_end_time - seismogram.begin_time) / seismogram.delta) + 1
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


class TestTaper:
    @parametrize_with_cases("seismogram")
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
    TAPER_WIDTH: timedelta | float = timedelta(seconds=500)

    @parametrize_with_cases("seismogram")
    def test_window(self, seismogram: Seismogram) -> None:
        from pysmo.functions import window, time2index

        taper_width = self.TAPER_WIDTH

        window_begin_time = seismogram.begin_time + timedelta(seconds=600)
        window_end_time = window_begin_time + timedelta(seconds=1000)
        windowed_seis = window(
            seismogram,
            window_begin_time,
            window_end_time,
            taper_width,
            same_shape=True,
            clone=True,
        )
        assert windowed_seis.begin_time == seismogram.begin_time
        assert windowed_seis.end_time == seismogram.end_time

        if isinstance(taper_width, timedelta):
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
    TAPER_WIDTH: timedelta | float = 0.1
