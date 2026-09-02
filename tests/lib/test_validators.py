import zoneinfo
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pysmo.lib.validators import (
    convert_to_ndarray,
    convert_to_timedelta,
    convert_to_utc_timestamp,
)


def test_convert_to_utc_timestamp_none() -> None:
    with pytest.raises(TypeError, match="Value is None"):
        convert_to_utc_timestamp(None)  # type: ignore[arg-type]


def test_convert_to_utc_timestamp_naive() -> None:
    dt = datetime(2020, 1, 1, 12, 0, 0)
    result = convert_to_utc_timestamp(dt)
    assert result == pd.Timestamp("2020-01-01 12:00:00", tz="UTC")


def test_convert_to_utc_timestamp_aware() -> None:
    ts = pd.Timestamp("2020-01-01 12:00:00", tz="UTC")
    result = convert_to_utc_timestamp(ts)
    assert result == ts


def test_convert_to_utc_timestamp_other_timezone() -> None:
    ts = pd.Timestamp("2020-01-01 12:00:00", tz="US/Eastern")
    result = convert_to_utc_timestamp(ts)
    assert result == pd.Timestamp("2020-01-01 17:00:00", tz="UTC")


def test_convert_to_utc_timestamp_str() -> None:
    result = convert_to_utc_timestamp("2020-01-01T12:00:00Z")
    assert result == pd.Timestamp("2020-01-01 12:00:00", tz="UTC")


def test_convert_to_timedelta() -> None:
    assert convert_to_timedelta(10) == pd.Timedelta(seconds=10)
    assert convert_to_timedelta(2.5) == pd.Timedelta(seconds=2.5)
    assert convert_to_timedelta("10s") == pd.Timedelta(seconds=10)
    assert convert_to_timedelta(pd.Timedelta(seconds=10)) == pd.Timedelta(seconds=10)
    assert convert_to_timedelta(timedelta(seconds=10)) == pd.Timedelta(seconds=10)


def test_convert_to_ndarray() -> None:
    arr = convert_to_ndarray([1, 2, 3])
    assert isinstance(arr, np.ndarray)
    np.testing.assert_array_equal(arr, np.array([1, 2, 3]))


def test_convert_to_ndarray_from_tuple() -> None:
    arr = convert_to_ndarray((1, 2, 3))
    assert isinstance(arr, np.ndarray)
    np.testing.assert_array_equal(arr, np.array([1, 2, 3]))


def test_convert_to_ndarray_casts_integer_to_float() -> None:
    assert convert_to_ndarray([1, 2, 3]).dtype == np.float64
    assert convert_to_ndarray(np.array([1, 2, 3], dtype=np.int32)).dtype == np.float64


def test_convert_to_ndarray_preserves_float_dtype_and_identity() -> None:
    original = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    arr = convert_to_ndarray(original)
    assert arr is original
    assert arr.dtype == np.float32


def test_convert_to_ndarray_rejects_ndarray_subclass_passthrough() -> None:
    masked = np.ma.array([1.0, 2.0, 3.0], mask=[False, True, False])
    arr = convert_to_ndarray(masked)
    assert type(arr) is np.ndarray


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
def test_convert_to_utc_timestamp_always_utc(dt: datetime) -> None:
    result = convert_to_utc_timestamp(dt)
    assert result.tzinfo is not None
    assert str(result.tzinfo) == "UTC"
    assert result.timestamp() == pytest.approx(pd.Timestamp(dt).timestamp())


@given(
    values=st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=1,
    )
)
def test_convert_to_ndarray_preserves_values(values: list[float]) -> None:
    result = convert_to_ndarray(values)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, np.array(values))
