"""Pysmo provides functions that perform common operations on the types of data that
match pysmo's types.
"""

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
import numpy as np
import copy
from pysmo import Seismogram, MiniSeismogram, Location
from pysmo.lib.functions import (
    _azdist,
    _detrend,
    _normalize,
    _resample
)
from pysmo.lib.defaults import DEFAULT_ELLPS


def clone_to_miniseismogram(seismogram: Seismogram,
                            skip_data: bool = False) -> MiniSeismogram:
    """Create a MiniSeismogram object from another Seismogram.

    Parameters:
        seismogram: Seismogram object to clone.
        skip_data: Create clone without data.

    Returns:
        A copy of the original Seismogram object.

    Examples:
        Create a copy of a [SAC][pysmo.classes.sac.SAC] object without data:

        >>> from pysmo import SAC, MiniSeismogram, clone_to_miniseismogram
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> cloned_seis = clone_to_miniseismogram(original_seis, skip_data=True)
        >>> print(cloned_seis.data)
        []

        Create a copy of a [SAC][pysmo.classes.sac.SAC] object with data:

        >>> from pysmo import SAC, MiniSeismogram, clone_to_miniseismogram
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> cloned_seis = clone_to_miniseismogram(original_seis)
        >>> print(cloned_seis.data)
        [2302. 2313. 2345. ... 2836. 2772. 2723.]
    """

    cloned_seismogram = MiniSeismogram()
    cloned_seismogram.begin_time = copy.copy(seismogram.begin_time)
    cloned_seismogram.sampling_rate = copy.copy(seismogram.sampling_rate)
    if not skip_data:
        cloned_seismogram.data = copy.copy(seismogram.data)
    return cloned_seismogram


def normalize(seismogram: Seismogram) -> MiniSeismogram:
    """Normalize a seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalized seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.classes.mini.MiniSeismogram]
        class (and classes that inherit from it). Thus, if
        you intend normalizing seismogram data **in-place**,
        instead of writing:

        ```python
        my_seis.data = normalize(my_seis)
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
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    clone.data = _normalize(seismogram)
    return clone


def detrend(seismogram: Seismogram) -> MiniSeismogram:
    """Remove linear and/or constant trends from a seismogram.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Detrended seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.classes.mini.MiniSeismogram]
        class (and classes that inherit from it). Thus, if
        you intend detrending seismogram data **in-place**,
        instead of writing:

        ```python
        my_seis.data = detrend(my_seis)
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
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    clone.data = _detrend(seismogram)
    return clone


def resample(seismogram: Seismogram, sampling_rate: float) -> MiniSeismogram:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        sampling_rate: New sampling rate.

    Returns:
        Resampled seismogram.

    Note:
        This function is also available as a method in the
        [MiniSeismogram][pysmo.classes.mini.MiniSeismogram]
        class (and classes that inherit from it). Thus, if
        you intend resample seismogram data **in-place**,
        instead of writing:

        ```python
        my_seis.data = resample(my_seis)
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
        >>> original_sampling_rate = original_seis.sampling_rate
        >>> new_sampling_rate = original_sampling_rate * 2
        >>> resampled_seis = resample(original_seis, new_sampling_rate)
        >>> len(resampled_seis)
        90000
    """
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    clone.data = _resample(seismogram, sampling_rate)
    clone.sampling_rate = sampling_rate
    return clone


def plotseis(*seismograms: Seismogram, outfile: str = "", showfig: bool = True,
             title: str = "", **kwargs: dict) -> plt.FigureBase:
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
    legend: bool = False
    fig = plt.figure()
    for seis in seismograms:
        start = mdates.date2num(seis.begin_time)
        end = mdates.date2num(seis.end_time)
        time = np.linspace(start, end, len(seis))
        try:
            kwargs['label'] = seis.label  # type: ignore
            legend = True
        except AttributeError:
            pass
        plt.plot(time, seis.data, **kwargs)
    if legend:
        plt.legend()
    plt.xlabel('Time')
    plt.gcf().autofmt_xdate()
    fmt = mdates.DateFormatter('%H:%M:%S')
    plt.gca().xaxis.set_major_formatter(fmt)
    if not title:
        left, _ = plt.xlim()
        title = mdates.num2date(left).strftime('%Y-%m-%d %H:%M:%S')
    plt.title(title)
    if outfile:
        plt.savefig(outfile)
    if showfig:
        plt.show()
    return fig


def azimuth(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate azimuth between two points.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Azimuth in degrees from point 1 to point 2.

    Examples:
        >>> from pysmo import SAC, azimuth
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth(sacobj.event, sacobj.station)
        181.9199258637492
        >>> # Use Clarke 1966 instead of default
        >>> azimuth(sacobj.event, sacobj.station, ellps='clrk66')
        181.92001941872516
    """
    return _azdist(lat1=point1.latitude, lon1=point1.longitude,
                   lat2=point2.latitude, lon2=point2.longitude,
                   ellps=ellps)[0]


def backazimuth(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate backazimuth (in DEG) between two points.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Backzimuth in degrees from point 2 to point 1

    Examples:
        >>> from pysmo import SAC, backazimuth
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> backazimuth(sacobj.event, sacobj.station)
        2.4677533885335947
        >>> # Use Clarke 1966 instead of default
        >>> backazimuth(sacobj.event, sacobj.station, ellps='clrk66')
        2.467847115319614
    """
    return _azdist(lat1=point1.latitude, lon1=point1.longitude,
                   lat2=point2.latitude, lon2=point2.longitude,
                   ellps=ellps)[1]


def distance(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate the great circle distance (in metres) between two points.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for distance calculation

    Returns:
        Great Circle Distance in metres.

    Examples:
        >>> from pysmo import SAC, distance
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> distance(sacobj.event, sacobj.station)
        1889154.9940066522
        >>> # Use Clarke 1966 instead of default
        >>> distance(sacobj.event, sacobj.station, ellps='clrk66')
        1889121.778136402
    """
    return _azdist(lat1=point1.latitude, lon1=point1.longitude,
                   lat2=point2.latitude, lon2=point2.longitude,
                   ellps=ellps)[2]