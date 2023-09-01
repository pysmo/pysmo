"""Pysmo provides functions that perform common operations on the types of data that
match pysmo's types.
"""

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
import scipy.signal  # type: ignore
import numpy as np
import copy
from pysmo import Seismogram, MiniSeismogram, Location
from pysmo.lib.functions import _azdist
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
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalized seismogram.

    Examples:
        >>> import numpy as np
        >>> from pysmo import SAC, normalize
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> normalized_seis = normalize(original_seis)
        >>> assert np.max(normalized_seis.data) <= 1
        True
    """
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    norm = np.max(np.abs(seismogram.data))
    clone.data = seismogram.data / norm
    return clone


def detrend(seismogram: Seismogram) -> MiniSeismogram:
    """Remove linear and/or constant trends from SAC object data.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Detrended seismogram.

    Examples:
        >>> import numpy as np
        >>> from pysmo import SAC, detrend
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> detrended_seis = detrend(original_seis)
        >>> assert np.mean(detrended_seis.data) == 0
        True
    """
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    clone.data = scipy.signal.detrend(seismogram.data)
    return clone


def resample(seismogram: Seismogram, sampling_rate: float) -> MiniSeismogram:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        sampling_rate: New sampling rate.

    Returns:
        Detrended seismogram.

    Examples:
        >>> from pysmo import SAC, resample
        >>> original_seis = SAC.from_file('testfile.sac').seismogram
        >>> len(original_seis)
        20000
        >>> original_sampling_rate = original_seis.sampling_rate
        >>> new_sampling_rate = original_sampling_rate * 2
        >>> resampled_seis = resample(original_seis, new_sampling_rate)
        >>> len(resampled_seis)
        10000
    """
    len_in = len(seismogram)
    sampling_rate_in = seismogram.sampling_rate
    len_out = int(len_in * sampling_rate_in / sampling_rate)
    clone = clone_to_miniseismogram(seismogram, skip_data=True)
    clone.data = scipy.signal.resample(seismogram.data, len_out)
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
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = azimuth(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = azimuth(sacobj.event, sacobj.station, ellps='clrk66')

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
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = backazimuth(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = backazimuth(sacobj.event, sacobj.station, ellps='clrk66')
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
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = distance(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = distance(sacobj.event, sacobj.station, ellps='clrk66')
    """
    return _azdist(lat1=point1.latitude, lon1=point1.longitude,
                   lat2=point2.latitude, lon2=point2.longitude,
                   ellps=ellps)[2]
