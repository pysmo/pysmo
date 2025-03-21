"""Pysmo provides functions that perform common operations on the types of data that
match pysmo's types.
"""

from pysmo import Seismogram, MiniSeismogram
from pysmo._lib.functions import lib_detrend, lib_normalize, lib_resample
from datetime import datetime, timedelta
from math import floor, ceil
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.figure
import numpy as np
import numpy.typing as npt

__all__ = [
    "crop",
    "detrend",
    "normalize",
    "resample",
    "time_array",
    "unix_time_array",
    "plotseis",
]


def crop(
    seismogram: Seismogram, new_begin_time: datetime, new_end_time: datetime
) -> MiniSeismogram:
    """Shorten a seismogram by providing a start and end time

    Parameters:
        seismogram: Seismogram object.
        new_begin_time: Start time.
        new_end_time: End time.

    Returns:
        Cropped seismogram.

    Examples:
        >>> from pysmo import crop
        >>> from pysmo.classes import SAC
        >>> from datetime import timedelta
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> new_begin_time = original_seis.begin_time + timedelta(seconds=10)
        >>> new_end_time = original_seis.end_time - timedelta(seconds=10)
        >>> cropped_seis = crop(original_seis, new_begin_time, new_end_time)

    Note:
        The returned seismogram may not have the exact new begin and end
        times that are specified as input, as no resampling is performed.
        Instead the nearest earlier sample is used as new begin time, and the
        nearest later sample as new end time.
    """
    old_begin_time = seismogram.begin_time

    if old_begin_time > new_begin_time:
        raise ValueError("new_begin_time cannot be before seismogram.begin_time")
    if seismogram.end_time < new_end_time:
        raise ValueError("new_end_time cannot be after seismogram.end_time")
    if new_begin_time > new_end_time:
        raise ValueError("new_begin_time cannot be after new_end_time")

    start_index = floor(
        (new_begin_time - old_begin_time).total_seconds() / seismogram.delta
    )
    end_index = ceil((new_end_time - old_begin_time).total_seconds() / seismogram.delta)

    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = seismogram.data[start_index:end_index]
    clone.begin_time = seismogram.begin_time + timedelta(
        seconds=clone.delta * start_index
    )
    return clone


def normalize(seismogram: Seismogram) -> MiniSeismogram:
    """Normalize a seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalized seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.MiniSeismogram]
        class. Thus, if you intend normalizing data of a
        MiniSeismogram object **in-place**, instead of
        writing:

        ```python
        my_seis.data = normalize(my_seis).data
        ```

        you should instead use:

        ```python
        my_seis.normalize()
        ```

    Examples:
        >>> import numpy as np
        >>> from pysmo import SAC, normalize
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> normalized_seis = normalize(original_seis)
        >>> assert np.max(normalized_seis.data) <= 1
        True
    """
    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = lib_normalize(seismogram)
    return clone


def detrend(seismogram: Seismogram) -> MiniSeismogram:
    """Remove linear and/or constant trends from a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Detrended seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.MiniSeismogram]
        class. Thus, if you intend detrending data of a
        MiniSeismogram object **in-place**, instead of
        writing:

        ```python
        my_seis.data = detrend(my_seis).data
        ```

        you should instead use:

        ```python
        my_seis.detrend()
        ```

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
    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = lib_detrend(seismogram)
    return clone


def resample(seismogram: Seismogram, delta: float) -> MiniSeismogram:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        delta: New sampling interval.

    Returns:
        Resampled seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.MiniSeismogram]
        class. Thus, if you intend resampling data of a
        MiniSeismogram object **in-place**, instead of
        writing:

        ```python
        my_seis.data = resample(my_seis).data
        ```

        you should instead use:

        ```python
        my_seis.resample()
        ```

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
    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = lib_resample(seismogram, delta)
    clone.delta = delta
    return clone


def time_array(seismogram: Seismogram) -> npt.NDArray:
    """Create an array containing Matplotlib dates (number of days since 1970)
    of each point in the Seismogram data.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Array containing the Matplotlib dates of seismogram data.

    Examples:
        >>> from pysmo import SAC, time_array
        >>> my_seis = SAC.from_file('testfile.sac').seismogram
        >>> seis_data = my_seis.data
        >>> seis_times = time_array(my_seis)
        >>> for t, v in zip(seis_times, seis_data):
        ...     print(t,v)
        ...
        12843.30766388889 2302.0
        12843.307664120372 2313.0
        12843.307664351854 2345.0
        12843.307664583335 2377.0
        ...
    """
    start = mdates.date2num(seismogram.begin_time)
    end = mdates.date2num(seismogram.end_time)
    return np.linspace(start, end, len(seismogram))


def unix_time_array(seismogram: Seismogram) -> npt.NDArray:
    """Create an array containing unix epoch dates (number of seconds since 1970)
    of each point in the Seismogram data.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Array containing the unix epoch times of seismogram data.

    Examples:
        >>> from pysmo import SAC, unix_time_array
        >>> my_seis = SAC.from_file('testfile.sac').seismogram
        >>> seis_data = my_seis.data
        >>> seis_times = unix_time_array(my_seis)
        >>> for t, v in zip(seis_times, seis_data):
        ...     print(t,v)
        ...
        1109661782.16 2302.0
        1109661782.18 2313.0
        1109661782.2 2345.0
        1109661782.22 2377.0
        ...
    """
    start = seismogram.begin_time.timestamp()
    end = seismogram.end_time.timestamp()
    return np.linspace(start, end, len(seismogram))


def plotseis(
    *seismograms: Seismogram,
    outfile: str = "",
    showfig: bool = True,
    title: str = "",
    **kwargs: dict,
) -> matplotlib.figure.Figure:
    """Plot Seismogram objects.

    Parameters:
        seismograms: One or more seismogram objects. If a 'label' attribute is found
                     it will be used to label the trace in the plot.
        outfile: Optionally save figure to this filename.
        showfig: Display figure.
        title: Optionally set figure title.
        kwargs: Optionally add kwargs to pass to the plot command

    Examples:
        >>> from pysmo import SAC, plotseis
        >>> seis = SAC.from_file('testfile.sac').seismogram
        >>> plotseis(seis)
    """
    fig = plt.figure()
    for seis in seismograms:
        time = time_array(seis)
        plt.plot(time, seis.data, scalex=True, scaley=True, **kwargs)
    plt.xlabel("Time")
    plt.gcf().autofmt_xdate()
    fmt = mdates.DateFormatter("%H:%M:%S")
    plt.gca().xaxis.set_major_formatter(fmt)
    if not title:
        left, _ = plt.xlim()
        title = mdates.num2date(left).strftime("%Y-%m-%d %H:%M:%S")
    plt.title(title)
    if outfile:
        plt.savefig(outfile)
    if showfig:
        plt.show()
    return fig
