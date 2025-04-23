from copy import deepcopy
from pysmo import Seismogram
from datetime import datetime, timedelta
from math import floor, ceil
from typing import Literal, overload
import scipy.signal
import numpy as np

__all__ = [
    "crop",
    "detrend",
    "normalize",
    "resample",
    "time2index",
]


@overload
def crop(
    seismogram: Seismogram,
    begin_time: datetime,
    end_time: datetime,
    clone: Literal[False] = False,
) -> None: ...


@overload
def crop[T: Seismogram](
    seismogram: T, begin_time: datetime, end_time: datetime, clone: Literal[True]
) -> T: ...


def crop[T: Seismogram](
    seismogram: T, begin_time: datetime, end_time: datetime, clone: bool = False
) -> None | T:
    """Shorten a seismogram by providing a start and end time.

    Parameters:
        seismogram: [`Seismogram`][pysmo.Seismogram] object.
        begin_time: New start time.
        end_time: New end time.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Cropped [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        >>> from pysmo.functions import crop
        >>> from pysmo.classes import SAC
        >>> from datetime import timedelta
        >>> sac_seis = SAC.from_file('testfile.sac').seismogram
        >>> new_begin_time = sac_seis.begin_time + timedelta(seconds=10)
        >>> new_end_time = sac_seis.end_time - timedelta(seconds=10)
        >>> crop(sac_seis, new_begin_time, new_end_time)

    Note:
        The returned seismogram may not have the exact new begin and end
        times that are specified as input, as no resampling is performed.
        Instead the nearest earlier sample is used as new begin time, and the
        nearest later sample as new end time.
    """

    if seismogram.begin_time > begin_time:
        raise ValueError("new begin_time cannot be before seismogram.begin_time")

    if seismogram.end_time < end_time:
        raise ValueError("new end_time cannot be after seismogram.end_time")

    if begin_time > end_time:
        raise ValueError("new begin_time cannot be after end_time")

    if clone is True:
        seismogram = deepcopy(seismogram)

    start_index = time2index(seismogram, begin_time, "floor")
    end_index = time2index(seismogram, end_time, "ceil")

    seismogram.data = seismogram.data[start_index : end_index + 1]
    seismogram.begin_time = seismogram.begin_time + seismogram.delta * start_index

    if clone is True:
        return seismogram

    return None


@overload
def detrend(seismogram: Seismogram, clone: Literal[False] = False) -> None: ...


@overload
def detrend[T: Seismogram](seismogram: T, clone: Literal[True]) -> T: ...


def detrend[T: Seismogram](seismogram: T, clone: bool = False) -> None | T:
    """Remove linear and/or constant trends from a seismogram.

    Parameters:
        seismogram: Seismogram object.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Detrended [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        >>> import numpy as np
        >>> import pytest
        >>> from pysmo.functions detrend
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file('testfile.sac').seismogram
        >>> assert 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-11)
        False
        >>> detrend(sac_seis)
        >>> assert 0 == pytest.approx(np.mean(sac_seis.data), abs=1e-11)
        True
    """
    if clone is True:
        seismogram = deepcopy(seismogram)

    seismogram.data = scipy.signal.detrend(seismogram.data)

    if clone is True:
        return seismogram

    return None


@overload
def normalize(
    seismogram: Seismogram,
    clone: Literal[False] = False,
    t1: datetime | None = None,
    t2: datetime | None = None,
) -> None: ...


@overload
def normalize[T: Seismogram](
    seismogram: T,
    clone: Literal[True],
    t1: datetime | None = None,
    t2: datetime | None = None,
) -> T: ...


def normalize[T: Seismogram](
    seismogram: T,
    clone: bool = False,
    t1: datetime | None = None,
    t2: datetime | None = None,
) -> None | T:
    """Normalize a seismogram with its absolute max value.

    Parameters:
        seismogram: Seismogram object.
        clone: Operate on a clone of the input seismogram.
        t1: Optionally restrict searching of maximum to time after this time.
        t2: Optionally restrict searching of maximum to time before this time.

    Returns:
        Normalized [`Seismogram`][pysmo.Seismogram] object if `clone=True`.

    Examples:
        >>> import numpy as np
        >>> from pysmo.functions import normalize
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file('testfile.sac').seismogram
        >>> normalize(sac_seis)
        >>> assert np.max(sac_seis.data) <= 1
        True
    """

    if clone is True:
        seismogram = deepcopy(seismogram)

    start_index = None
    if t1 is not None:
        start_index = time2index(seismogram, t1, "floor")

    end_index = None
    if t2 is not None:
        end_index = time2index(seismogram, t2, "ceil")

    seismogram.data /= np.max(np.abs(seismogram.data[start_index:end_index]))

    if clone is True:
        return seismogram

    return None


@overload
def resample(
    seismogram: Seismogram, delta: timedelta, clone: Literal[False] = False
) -> None: ...


@overload
def resample[T: Seismogram](
    seismogram: T, delta: timedelta, clone: Literal[True]
) -> T: ...


def resample[T: Seismogram](
    seismogram: T, delta: timedelta, clone: bool = False
) -> None | T:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        delta: New sampling interval.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Resampled [`Seismogram`][pysmo.Seismogram] object if called with `clone=True`.

    Examples:
        >>> from pysmo.functions import resample
        >>> from pysmo.classes import SAC
        >>> sac_seis = SAC.from_file('testfile.sac').seismogram
        >>> len(sac_seis)
        180000
        >>> original_delta = sac_seis.delta
        >>> new_delta = original_delta * 2
        >>> resample(sac_seis, new_delta)
        >>> len(sac_seis)
        90000
    """

    if clone is True:
        seismogram = deepcopy(seismogram)

    npts = int(len(seismogram) * seismogram.delta / delta)
    seismogram.data = scipy.signal.resample(seismogram.data, npts)
    seismogram.delta = delta

    if clone is True:
        return seismogram

    return None


def time2index(
    seismogram: Seismogram,
    time: datetime,
    method: Literal["round", "ceil", "floor"] = "round",
) -> int:
    """Retuns data index corresponding to a given time.

    This function converts time to index of a seismogram's data array. In most
    cases the time will not have an exact match in the data array. This
    function allows choosing how to select the index to return when that is
    the case with the method parameter:

    - round: round to nearest index.
    - ceil: always round up to next higher index.
    - floor: always round down to next lower index.

    Parameters:
        seismogram: Seismogram object.
        time: Time to convert to index.
        method: Method to use for selecting the index to return.

    Returns:
        Index of the sample corresponding to the given time.
    """

    if not seismogram.begin_time <= time <= seismogram.end_time:
        raise ValueError("time must be between begin_time and end_time")

    if method not in ["round", "ceil", "floor"]:
        raise ValueError("method must be 'round', 'ceil' or 'floor'")

    if method == "ceil":
        return ceil((time - seismogram.begin_time) / seismogram.delta)

    if method == "floor":
        return floor((time - seismogram.begin_time) / seismogram.delta)

    return round((time - seismogram.begin_time) / seismogram.delta)
