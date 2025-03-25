"""Pysmo provides functions that perform common operations on the types of data that
match pysmo's types.
"""

from pysmo import Seismogram
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.figure
import numpy as np
import numpy.typing as npt

__all__ = [
    "time_array",
    "unix_time_array",
    "plotseis",
]


def time_array(seismogram: Seismogram) -> npt.NDArray:
    """Create an array containing Matplotlib dates.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Array containing the Matplotlib dates of seismogram data.
        array containing the Matplotlib dates (number of days since 1970)
        of each point in the seismogram data.

    Examples:
        >>> from pysmo.tools.plotseis import time_array
        >>> from pysmo.classes import SAC
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
    """Create an array containing unix epoch dates.

    Parameters:
        seismogram: Seismogram object.

    Returns:
        array containing the unix epoch times (number of seconds since 1970)
        of each point in the seismogram data.

    Examples:
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotseis import unix_time_array
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
