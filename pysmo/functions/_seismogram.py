from pysmo import Seismogram
from datetime import datetime, timedelta
from copy import deepcopy
from math import floor, ceil
from typing import Literal
import scipy.signal
import numpy as np

__all__ = [
    "crop",
    "detrend",
    "normalize",
    "resample",
    "time2index",
]


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
        Index of the given sample corresponding to the given time.
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


def crop[T: Seismogram](seismogram: T, begin_time: datetime, end_time: datetime) -> T:
    """Shorten a seismogram by providing a start and end time.

    Parameters:
        seismogram: Seismogram object.
        begin_time: New start time.
        end_time: New end time.

    Returns:
        Cropped Seismogram object.

    Examples:
        >>> from pysmo import crop
        >>> from pysmo.classes import SAC
        >>> from datetime import timedelta
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> begin_time = original_seis.begin_time + timedelta(seconds=10)
        >>> end_time = original_seis.end_time - timedelta(seconds=10)
        >>> cropped_seis = crop(original_seis, begin_time, end_time)

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

    start_index = time2index(seismogram, begin_time, "floor")
    end_index = time2index(seismogram, end_time, "ceil")

    clone = deepcopy(seismogram)
    clone.data = seismogram.data[start_index : end_index + 1]
    clone.begin_time = seismogram.begin_time + clone.delta * start_index
    return clone


def normalize[T: Seismogram](seismogram: T) -> T:
    """Normalize a seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalized Seismogram object.

    Examples:
        >>> import numpy as np
        >>> from pysmo import SAC, normalize
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> normalized_seis = normalize(original_seis)
        >>> assert np.max(normalized_seis.data) <= 1
        True
    """

    clone = deepcopy(seismogram)
    norm = np.max(np.abs(seismogram.data))
    clone.data = seismogram.data / norm
    return clone


def detrend[T: Seismogram](seismogram: T) -> T:
    """Remove linear and/or constant trends from a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Detrended Seismogram object.

    Examples:
        >>> import numpy as np
        >>> import pytest
        >>> from pysmo import SAC, detrend
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> assert 0 == pytest.approx(np.mean(original_seis.data), abs=1e-11)
        False
        >>> detrended_seis = detrend(original_seis)
        >>> assert 0 == pytest.approx(np.mean(detrended_seis.data), abs=1e-11)
        True
    """
    clone = deepcopy(seismogram)
    clone.data = scipy.signal.detrend(seismogram.data)
    return clone


def resample[T: Seismogram](seismogram: T, delta: timedelta) -> T:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        delta: New sampling interval.

    Returns:
        Resampled Seismogram object.

    Examples:
        >>> from pysmo import SAC, resample
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> len(original_seis)
        180000
        >>> original_delta = original_seis.delta
        >>> new_delta = original_delta * 2
        >>> resampled_seis = resample(original_seis, new_delta)
        >>> len(resampled_seis)
        90000
    """

    npts = int(len(seismogram) * seismogram.delta / delta)
    clone = deepcopy(seismogram)
    clone.data = scipy.signal.resample(seismogram.data, npts)
    clone.delta = delta
    return clone
