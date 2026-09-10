import zoneinfo
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo.lib.converters import (
    to_complex_list,
    to_float_list,
    to_longitude,
    to_ndarray,
    to_strict_int,
    to_timedelta,
    to_utc_timestamp,
)


def test_to_utc_timestamp_none() -> None:
    with pytest.raises(TypeError, match="Value is None"):
        to_utc_timestamp(None)  # type: ignore[arg-type]


def test_to_utc_timestamp_nat() -> None:
    with pytest.raises(ValueError, match="not a valid timestamp"):
        to_utc_timestamp(pd.NaT)  # type: ignore[arg-type]


def test_to_longitude() -> None:
    assert to_longitude(-180) == 180.0  # antimeridian folded onto +180
    assert to_longitude(-180.0) == 180.0
    assert to_longitude(180) == 180.0
    assert to_longitude(-179.9) == -179.9
    assert to_longitude("45") == 45.0
    # out of range: passed through unchanged for a downstream validator
    assert to_longitude(-180.5) == -180.5
    assert to_longitude(200) == 200.0


def test_to_utc_timestamp_naive() -> None:
    dt = datetime(2020, 1, 1, 12, 0, 0)
    result = to_utc_timestamp(dt)
    assert result == pd.Timestamp("2020-01-01 12:00:00", tz="UTC")


def test_to_utc_timestamp_aware() -> None:
    ts = pd.Timestamp("2020-01-01 12:00:00", tz="UTC")
    result = to_utc_timestamp(ts)
    assert result == ts


def test_to_utc_timestamp_other_timezone() -> None:
    ts = pd.Timestamp("2020-01-01 12:00:00", tz="US/Eastern")
    result = to_utc_timestamp(ts)
    assert result == pd.Timestamp("2020-01-01 17:00:00", tz="UTC")


def test_to_utc_timestamp_str() -> None:
    result = to_utc_timestamp("2020-01-01T12:00:00Z")
    assert result == pd.Timestamp("2020-01-01 12:00:00", tz="UTC")


def test_to_timedelta() -> None:
    assert to_timedelta(10) == pd.Timedelta(seconds=10)
    assert to_timedelta(2.5) == pd.Timedelta(seconds=2.5)
    assert to_timedelta("10s") == pd.Timedelta(seconds=10)
    assert to_timedelta(pd.Timedelta(seconds=10)) == pd.Timedelta(seconds=10)
    assert to_timedelta(timedelta(seconds=10)) == pd.Timedelta(seconds=10)


def test_to_ndarray() -> None:
    arr = to_ndarray([1, 2, 3])
    assert isinstance(arr, np.ndarray)
    np.testing.assert_array_equal(arr, np.array([1, 2, 3]))


def test_to_ndarray_from_tuple() -> None:
    arr = to_ndarray((1, 2, 3))
    assert isinstance(arr, np.ndarray)
    np.testing.assert_array_equal(arr, np.array([1, 2, 3]))


def test_to_ndarray_casts_integer_to_float() -> None:
    assert to_ndarray([1, 2, 3]).dtype == np.float64
    assert to_ndarray(np.array([1, 2, 3], dtype=np.int32)).dtype == np.float64


def test_to_ndarray_preserves_float_dtype_and_identity() -> None:
    original = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    arr = to_ndarray(original)
    assert arr is original
    assert arr.dtype == np.float32


def test_to_ndarray_rejects_ndarray_subclass_passthrough() -> None:
    masked = np.ma.array([1.0, 2.0, 3.0], mask=[False, True, False])
    arr = to_ndarray(masked)
    assert type(arr) is np.ndarray


def test_to_complex_list() -> None:
    assert to_complex_list([1, 2.0, 3j]) == [1 + 0j, 2 + 0j, 3j]


def test_to_float_list() -> None:
    result = to_float_list([1, "2.5", np.float32(3)])  # type: ignore[list-item]
    assert result == [1.0, 2.5, 3.0]
    assert all(type(x) is float for x in result)


def test_to_strict_int() -> None:
    assert to_strict_int(3) == 3
    assert to_strict_int(3.0) == 3  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not a whole number"):
        to_strict_int(2.5)  # type: ignore[arg-type]


# ─────────────────────── Property-based tests ───────────────────────────────


@given(
    dt=st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2030, 1, 1),
        timezones=st.sampled_from(
            [
                UTC,
                zoneinfo.ZoneInfo("US/Eastern"),
                zoneinfo.ZoneInfo("Europe/Berlin"),
                zoneinfo.ZoneInfo("Asia/Tokyo"),
            ]
        ),
    )
)
def test_to_utc_timestamp_always_utc(dt: datetime) -> None:
    result = to_utc_timestamp(dt)
    assert result.tzinfo is not None
    assert str(result.tzinfo) == "UTC"
    assert result.timestamp() == pytest.approx(pd.Timestamp(dt).timestamp())


@given(
    values=st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=1,
    )
)
def test_to_ndarray_preserves_values(values: list[float]) -> None:
    result = to_ndarray(values)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, np.array(values))
