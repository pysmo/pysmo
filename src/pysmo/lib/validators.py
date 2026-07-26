"""
Validators and converters for pysmo classes using [`attrs`][attrs].
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


def convert_to_utc_timestamp(value: pd.Timestamp | datetime | str) -> pd.Timestamp:
    """Convert a value to a [`pandas.Timestamp`][pandas.Timestamp] object with `#!py tzinfo=timezone.utc` set."""
    if value is None:
        raise TypeError("Value is None.")

    ts = pd.Timestamp(value)

    if ts.tz is None:
        return ts.tz_localize(timezone.utc)

    return ts.tz_convert(timezone.utc)


def convert_to_timedelta(
    value: pd.Timedelta | timedelta | float | int | str,
) -> pd.Timedelta:
    """Convert a value to a [`pandas.Timedelta`][pandas.Timedelta] object.

    If the value is a float or int, it is assumed to be in seconds.
    """
    if isinstance(value, (float, int)):
        return pd.Timedelta(value, unit="s")
    return pd.Timedelta(value)


def convert_to_ndarray(value: np.ndarray | list | tuple) -> np.ndarray:
    """Convert a value to a [`numpy.ndarray`][numpy.ndarray] object."""
    return np.asanyarray(value)
