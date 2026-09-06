"""Direct coverage of the `replace` keyword contract.

`replace=True` returns a new, fully independent seismogram of the same
concrete type for value objects, and raises `TypeError` for `SacSeismogram`
(a live projection of an open SAC file, not a value object). `replace=False`
keeps the historical in-place behaviour.
"""

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from pysmo import Seismogram
from pysmo.classes import SacSeismogram
from pysmo.functions import crop, detrend, normalize, pad, resample, taper

VALUE_OBJECT_FIXTURES = ["mini_seismogram", "geocsv_seismogram", "mseed_seismogram"]


@pytest.fixture(params=VALUE_OBJECT_FIXTURES, ids=VALUE_OBJECT_FIXTURES)
def value_seismogram(request: pytest.FixtureRequest) -> Seismogram:
    return request.getfixturevalue(request.param)


class TestReplaceReturnsIndependentObject:
    def test_same_concrete_type(self, value_seismogram: Seismogram) -> None:
        result = detrend(value_seismogram, replace=True)
        assert type(result) is type(value_seismogram)

    def test_input_untouched(self, value_seismogram: Seismogram) -> None:
        original = deepcopy(value_seismogram)
        detrend(value_seismogram, replace=True)
        np.testing.assert_array_equal(value_seismogram.data, original.data)
        assert value_seismogram.begin_time == original.begin_time
        assert value_seismogram.delta == original.delta

    def test_returned_data_is_not_aliased(self, value_seismogram: Seismogram) -> None:
        original = value_seismogram.data.copy()
        result = detrend(value_seismogram, replace=True)
        result.data[:] = 0.0
        np.testing.assert_array_equal(value_seismogram.data, original)


class TestReplaceUnsupportedForProjection:
    def test_detrend_raises(self, sac_seismogram: SacSeismogram) -> None:
        with pytest.raises(TypeError):
            detrend(sac_seismogram, replace=True)

    def test_crop_raises(self, sac_seismogram: SacSeismogram) -> None:
        begin = sac_seismogram.begin_time + pd.Timedelta(seconds=1)
        end = sac_seismogram.end_time - pd.Timedelta(seconds=1)
        with pytest.raises(TypeError):
            crop(sac_seismogram, begin, end, replace=True)

    def test_input_not_mutated_when_raising(
        self, sac_seismogram: SacSeismogram
    ) -> None:
        original = sac_seismogram.data.copy()
        with pytest.raises(TypeError):
            detrend(sac_seismogram, replace=True)
        np.testing.assert_array_equal(sac_seismogram.data, original)


class TestReplaceFalseUnchanged:
    def test_in_place_returns_none_and_mutates(
        self, value_seismogram: Seismogram
    ) -> None:
        before = value_seismogram.data.copy()
        result = detrend(value_seismogram)
        assert result is None
        assert not np.array_equal(value_seismogram.data, before)


class TestNoAliasGuarantee:
    def test_crop_slice_is_copied(self, value_seismogram: Seismogram) -> None:
        begin = value_seismogram.begin_time + 5 * value_seismogram.delta
        end = value_seismogram.end_time - 5 * value_seismogram.delta
        original = value_seismogram.data.copy()
        cropped = crop(value_seismogram, begin, end, replace=True)
        cropped.data[:] = 0.0
        np.testing.assert_array_equal(value_seismogram.data, original)

    def test_taper_starts_from_a_copy(self, value_seismogram: Seismogram) -> None:
        original = value_seismogram.data.copy()
        tapered = taper(value_seismogram, 0.2, replace=True)
        tapered.data[:] = 0.0
        np.testing.assert_array_equal(value_seismogram.data, original)


class TestNoOpBranchesStillCopy:
    def test_pad_no_op_returns_independent_copy(
        self, value_seismogram: Seismogram
    ) -> None:
        original = value_seismogram.data.copy()
        padded = pad(
            value_seismogram,
            value_seismogram.begin_time,
            value_seismogram.end_time,
            replace=True,
        )
        assert len(padded.data) == len(value_seismogram.data)
        padded.data[:] = 0.0
        np.testing.assert_array_equal(value_seismogram.data, original)

    def test_resample_no_op_returns_independent_copy(
        self, value_seismogram: Seismogram
    ) -> None:
        original = value_seismogram.data.copy()
        resampled = resample(value_seismogram, value_seismogram.delta, replace=True)
        assert len(resampled.data) == len(value_seismogram.data)
        resampled.data[:] = 0.0
        np.testing.assert_array_equal(value_seismogram.data, original)


def test_normalize_replace_matches_in_place(value_seismogram: Seismogram) -> None:
    in_place = deepcopy(value_seismogram)
    replaced = normalize(value_seismogram, replace=True)
    normalize(in_place)
    np.testing.assert_array_equal(replaced.data, in_place.data)
