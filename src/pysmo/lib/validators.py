"""Validators and converters for pysmo's `attrs` classes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import Attribute


def validate_nonzero[T: int | float | complex | None](
    instance: object, attribute: Attribute[T], value: T
) -> None:
    """Ensure `value` is not exactly zero. Either sign is otherwise permitted."""
    if value == 0:
        raise ValueError(f"{attribute.name} must not be zero.")


def convert_to_utc_timestamp(value: pd.Timestamp | datetime | str) -> pd.Timestamp:
    """Convert a value to a UTC `Timestamp` (`#!py tzinfo=timezone.utc`).

    See [`Timestamp`][pandas.Timestamp].
    """
    if value is None:
        raise TypeError("Value is None.")

    ts = pd.Timestamp(value)

    if pd.isna(ts):
        raise ValueError(f"{value!r} is not a valid timestamp.")

    if ts.tz is None:
        return ts.tz_localize(UTC)

    return ts.tz_convert(UTC)


def convert_to_longitude(value: float | str) -> float:
    """Convert a value to a `float` longitude in degrees, folding -180 onto +180.

    -180 and +180 name the same meridian; +180 is kept as the single
    canonical value so two spellings of the antimeridian cannot compare
    unequal. Values genuinely outside `[-180, 180]` are returned unchanged
    for a downstream validator to reject.
    """
    longitude = float(value)
    return 180.0 if longitude == -180.0 else longitude


def convert_to_timedelta(
    value: pd.Timedelta | timedelta | float | int | str,
) -> pd.Timedelta:
    """Convert a value to a `Timedelta`.

    A float or int is assumed to be in seconds.
    See [`Timedelta`][pandas.Timedelta].
    """
    if isinstance(value, (float, int)):
        return pd.Timedelta(value, unit="s")
    return pd.Timedelta(value)


def convert_to_ndarray(
    value: npt.NDArray[Any] | list[Any] | tuple[Any, ...],
) -> npt.NDArray[np.floating]:
    """Convert a value to a floating-point `ndarray`.

    Non-floating input (e.g. an integer list) is cast to `float64`; floating
    input keeps its own precision. `np.asarray`, not `np.asanyarray`, so an
    [`ndarray`][numpy.ndarray] subclass (masked array, `np.matrix`) does not
    leak through.
    """
    array = np.asarray(value)
    if np.issubdtype(array.dtype, np.floating):
        return array
    return array.astype(np.float64)


def convert_to_complex_list(value: list[complex]) -> list[complex]:
    """Convert an iterable of numbers to a list of `complex` values.

    See [`complex`][].
    """
    return [complex(item) for item in value]
