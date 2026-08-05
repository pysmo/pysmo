from copy import deepcopy

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from syrupy.assertion import SnapshotAssertion

from pysmo import Seismogram
from pysmo.functions._seismogram import _WindowType
from pysmo.tools.plotutils import time_array
from tests.test_helpers import assert_seismogram_modification


def test_time2index(seismogram: Seismogram) -> None:
    from pysmo.functions import time2index

    assert time2index(seismogram, seismogram.begin_time) == 0
    assert time2index(seismogram, seismogram.end_time) + 1 == len(seismogram.data)

    time = seismogram.begin_time + 10.1 * seismogram.delta
    assert time2index(seismogram, time) == 10

    time = seismogram.begin_time + 10.8 * seismogram.delta
    assert time2index(seismogram, time) == 11

    time = seismogram.begin_time - 10.8 * seismogram.delta
    assert time2index(seismogram, time, allow_out_of_bounds=True) == -11

    with pytest.raises(ValueError):
        time2index(seismogram, seismogram.begin_time - pd.Timedelta(seconds=1))
    with pytest.raises(ValueError):
        time2index(seismogram, seismogram.end_time + pd.Timedelta(seconds=1))


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


def test_normalize_zero_data_raises() -> None:
    """Normalising a seismogram with all-zero data must raise ValueError."""
    from pysmo import MiniSeismogram
    from pysmo.functions import normalize

    zero_seis = MiniSeismogram(
        begin_time=pd.Timestamp("2000-01-01", tz="UTC"),
        delta=pd.Timedelta(seconds=1),
        data=np.zeros(100),
    )
    with pytest.raises(ValueError, match="zero"):
        normalize(zero_seis)


def test_normalize_zero_window_raises() -> None:
    """Normalising with a time window that contains only zeros must raise ValueError."""
    from pysmo import MiniSeismogram
    from pysmo.functions import normalize

    data = np.ones(100)
    data[20:40] = 0.0
    seis = MiniSeismogram(
        begin_time=pd.Timestamp("2000-01-01", tz="UTC"),
        delta=pd.Timedelta(seconds=1),
        data=data,
    )
    t1 = seis.begin_time + 20 * seis.delta
    t2 = seis.begin_time + 39 * seis.delta
    with pytest.raises(ValueError, match="zero"):
        normalize(seis, t1=t1, t2=t2)


def test_normalize_snapshot(
    seismogram: Seismogram, snapshot: SnapshotAssertion
) -> None:
    """Test normalize output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the normalize function output remains
    consistent across code changes.
    """
    from pysmo.functions import normalize

    assert_seismogram_modification(seismogram, normalize, expected_data=snapshot)


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
            seismogram.begin_time - pd.Timedelta(seconds=1),
        )


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


def test_detrend(seismogram: Seismogram) -> None:
    """Detrend Seismogram object and verify mean is 0."""
    from pysmo.functions import detrend

    def check_detrended(seis: Seismogram) -> None:
        assert pytest.approx(np.mean(seis.data), abs=1e-6) == 0

    assert_seismogram_modification(
        seismogram, detrend, custom_assertions=check_detrended
    )


def test_detrend_snapshot(seismogram: Seismogram, snapshot: SnapshotAssertion) -> None:
    """Test detrend output against snapshot for regression testing.

    Uses syrupy snapshots to ensure the detrend function output remains
    consistent across code changes.
    """
    from pysmo.functions import detrend

    assert_seismogram_modification(seismogram, detrend, expected_data=snapshot)


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
        expected_length = len(seismogram.data) // 2
        assert abs(len(seis.data) - expected_length) <= 2, (
            "Length should be approximately halved"
        )

    assert_seismogram_modification(
        seismogram, resample, new_delta, custom_assertions=check_resampled
    )


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


def test_estimate_delta_odd_count() -> None:
    from pysmo.functions import estimate_delta

    deltas = [
        pd.Timedelta(seconds=1.0),
        pd.Timedelta(seconds=1.0) + pd.Timedelta(nanoseconds=1),
        pd.Timedelta(seconds=1.0),
    ]
    assert estimate_delta(deltas) == pd.Timedelta(seconds=1.0)


def test_estimate_delta_even_count_picks_low_median() -> None:
    from pysmo.functions import estimate_delta

    deltas = [pd.Timedelta(seconds=1.0), pd.Timedelta(seconds=2.0)]
    assert estimate_delta(deltas) == pd.Timedelta(seconds=1.0)


def test_estimate_delta_empty_raises() -> None:
    from pysmo.functions import estimate_delta

    with pytest.raises(ValueError, match="No deltas to estimate from"):
        estimate_delta([])


def test_merge_auto_delta_resamples_jittery_deltas() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1) + pd.Timedelta(nanoseconds=1),
        data=np.array([4.0, 5.0, 6.0]),
    )

    merged = merge([first, second], auto_delta=True, clone=True)
    assert merged.delta == pd.Timedelta(seconds=1)
    np.testing.assert_allclose(merged.data, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    # Neither input is mutated when clone=True.
    assert second.delta == pd.Timedelta(seconds=1) + pd.Timedelta(nanoseconds=1)


def test_merge() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([4.0, 5.0]),
    )

    merged = merge([first, second], clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert merged.begin_time == first.begin_time
    assert merged.delta == first.delta

    result = merge([first, second])
    assert result is None
    np.testing.assert_array_equal(first.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    np.testing.assert_array_equal(second.data, np.array([4.0, 5.0]))


def test_merge_out_of_order_input() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([4.0, 5.0]),
    )

    # `second` is passed first, even though `first` starts earlier.
    merged = merge([second, first], clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert merged.begin_time == first.begin_time

    # clone=False still mutates and returns the literal first list entry
    # (`second`), even though it is not chronologically first.
    result = merge([second, first])
    assert result is None
    np.testing.assert_array_equal(second.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert second.begin_time == first.begin_time
    np.testing.assert_array_equal(first.data, np.array([1.0, 2.0, 3.0]))


def test_merge_empty_seismogram_discarded() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    # Empty, and with a begin_time and delta that would otherwise be
    # inconsistent with the real data -- must not affect the merge at all.
    empty = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T05:00:00Z"),
        delta=pd.Timedelta(seconds=99),
        data=np.array([]),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([4.0, 5.0]),
    )

    merged = merge([first, empty, second], clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert merged.begin_time == first.begin_time


def test_merge_first_empty_is_still_mutation_target() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    empty = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T05:00:00Z"),
        delta=pd.Timedelta(seconds=99),
        data=np.array([]),
    )
    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([4.0, 5.0]),
    )

    # clone=True: the clone is based on `empty` (the first list entry),
    # even though it started out empty.
    merged = merge([empty, first, second], clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert merged.begin_time == first.begin_time
    assert merged.delta == first.delta
    assert empty.data.size == 0  # the original `empty` object is untouched

    # clone=False: `empty` itself is mutated in place and becomes the
    # merged result, even though it started out empty.
    result = merge([empty, first, second])
    assert result is None
    np.testing.assert_array_equal(empty.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert empty.begin_time == first.begin_time
    assert empty.delta == first.delta
    np.testing.assert_array_equal(first.data, np.array([1.0, 2.0, 3.0]))


def test_merge_all_empty_raises() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    empty1 = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([]),
    )
    empty2 = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([]),
    )

    with pytest.raises(ValueError, match="No non-empty seismograms"):
        merge([empty1, empty2])


def test_merge_no_seismograms_raises() -> None:
    from pysmo.functions import merge

    with pytest.raises(ValueError, match="No seismograms to merge"):
        merge([])


def test_merge_with_resampling() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(4),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:04Z"),
        delta=pd.Timedelta(milliseconds=500),
        data=np.full(8, 2.0),
    )

    merged = merge([first, second], delta=pd.Timedelta(seconds=1), clone=True)
    np.testing.assert_allclose(
        merged.data, np.array([1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0])
    )
    assert merged.delta == pd.Timedelta(seconds=1)
    assert second.delta == pd.Timedelta(milliseconds=500)


def test_merge_with_resampling_no_clone() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(4),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:04Z"),
        delta=pd.Timedelta(milliseconds=500),
        data=np.full(8, 2.0),
    )

    result = merge([first, second], delta=pd.Timedelta(seconds=1))
    assert result is None

    # The first seismogram is mutated in place and becomes the merged result.
    np.testing.assert_allclose(
        first.data, np.array([1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0])
    )
    assert first.delta == pd.Timedelta(seconds=1)

    # The second (non-first) input must not be mutated, even though it
    # needed resampling to match delta.
    assert second.delta == pd.Timedelta(milliseconds=500)
    np.testing.assert_array_equal(second.data, np.full(8, 2.0))


def test_merge_different_sampling_intervals_raise() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(milliseconds=500),
        data=np.ones(6),
    )

    with pytest.raises(ValueError, match="different sampling intervals"):
        merge([first, second])


def test_merge_gap_raises() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03.6Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )

    with pytest.raises(ValueError, match="Data gap of 0.600000 s"):
        merge([first, second])


def test_merge_allows_tiny_boundary_jitter() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03.0000005Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.full(2, 2.0),
    )

    merged = merge([first, second], clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 1.0, 1.0, 2.0, 2.0]))


def test_merge_matching_overlap_is_trimmed() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    # Overlaps the last sample of `first` (value 3.0) by exactly one full
    # sample interval; requires gap_tolerance_factor=1.0 to be tolerated.
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:02Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([3.0, 4.0, 5.0]),
    )

    merged = merge([first, second], gap_tolerance_factor=1.0, clone=True)
    np.testing.assert_array_equal(merged.data, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert merged.begin_time == first.begin_time
    assert merged.end_time == first.begin_time + merged.delta * 4


def test_merge_mismatched_overlap_raises() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0]),
    )
    # Overlaps by one full sample interval, but the overlapping sample
    # value does not match.
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:02Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([999.0, 4.0, 5.0]),
    )

    with pytest.raises(ValueError, match="do not match"):
        merge([first, second], gap_tolerance_factor=1.0)


def test_merge_negative_gap_tolerance_factor_raises() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:03Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )

    with pytest.raises(ValueError, match="gap_tolerance_factor must be non-negative"):
        merge([first, second], gap_tolerance_factor=-1)


def test_merge_overlap_exceeding_tolerance_raises() -> None:
    from pysmo import MiniSeismogram
    from pysmo.functions import merge

    first = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )
    # Overlaps by two full sample intervals, exceeding the default
    # gap_tolerance_factor.
    second = MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:30:01Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.ones(3),
    )

    with pytest.raises(ValueError, match="Data overlap of 2.000000 s"):
        merge([first, second])


def test_crop(seismogram: Seismogram) -> None:
    """Crop Seismogram object and verify cropped data."""
    from pysmo.functions import crop

    def check_no_crop(seis: Seismogram) -> None:
        assert len(seis.data) == len(seismogram.data)
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

    if len(seismogram.data) > 100:
        seis3 = deepcopy(seismogram)
        seis3.data = seis3.data[:100]
        new_begin_time = seis3.begin_time + seis3.delta
        new_end_time = seis3.end_time - seis3.delta
        cropped_seis = crop(seis3, new_begin_time, new_end_time, clone=True)
        assert all(cropped_seis.data == seis3.data[1:-1])


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
    @pytest.mark.mpl_image_compare(remove_text=True)
    def test_taper(self, seismogram: Seismogram) -> Figure:
        from pysmo.functions import taper

        seismogram.data = np.ones(len(seismogram.data))

        with pytest.raises(TypeError):
            _ = taper(seismogram, "abc", clone=True)  # type: ignore
        with pytest.raises(ValueError):
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
    TAPER_WIDTH: pd.Timedelta | float = pd.Timedelta(seconds=100)

    def test_window(self, seismogram: Seismogram) -> None:
        from pysmo.functions import time2index, window

        taper_width = self.TAPER_WIDTH

        window_begin_time = seismogram.begin_time + pd.Timedelta(seconds=150)
        window_end_time = window_begin_time + pd.Timedelta(seconds=300)
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

        if isinstance(taper_width, pd.Timedelta):
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
    TAPER_WIDTH: pd.Timedelta | float = 0.1


class TestWindowRampValidation:
    """window() must raise a clear ValueError when the ramp extends beyond the seismogram."""

    @pytest.fixture()
    def short_seismogram(self) -> Seismogram:
        from pysmo import MiniSeismogram

        return MiniSeismogram(
            begin_time=pd.Timestamp("2000-01-01", tz="UTC"),
            delta=pd.Timedelta(seconds=1),
            data=np.zeros(100),
        )

    def test_ramp_too_large_timedelta(self, short_seismogram: Seismogram) -> None:
        from pysmo.functions import window

        mid = short_seismogram.begin_time + pd.Timedelta(seconds=50)
        with pytest.raises(ValueError, match="ramp_width"):
            window(
                short_seismogram,
                window_begin_time=mid - pd.Timedelta(seconds=10),
                window_end_time=mid + pd.Timedelta(seconds=10),
                ramp_width=pd.Timedelta(
                    seconds=60
                ),  # exceeds available data on each side
            )

    def test_ramp_too_large_float(self, short_seismogram: Seismogram) -> None:
        from pysmo.functions import window

        # window of 10 s with ramp_width=5.0 → ramp = 50 s on each side;
        # seismogram only has ~50 s before the window start.
        window_begin = short_seismogram.begin_time + pd.Timedelta(seconds=5)
        window_end = window_begin + pd.Timedelta(seconds=10)
        with pytest.raises(ValueError, match="ramp_width"):
            window(
                short_seismogram,
                window_begin_time=window_begin,
                window_end_time=window_end,
                ramp_width=5.0,  # ramp = 50 s; only 5 s available before window
            )
