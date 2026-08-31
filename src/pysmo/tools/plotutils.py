"""Utilities for plotting with pysmo types.

Provides functions to convert a [`Seismogram`][pysmo.Seismogram]'s time axis
into arrays matplotlib can plot directly
([`time_array`][pysmo.tools.plotutils.time_array],
[`unix_time_array`][pysmo.tools.plotutils.unix_time_array],
[`relative_time_array`][pysmo.tools.plotutils.relative_time_array]), plus a
basic plotting helper ([`plotseis`][pysmo.tools.plotutils.plotseis]).
"""

from typing import Any

import matplotlib.dates as mdates
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd

from pysmo import Seismogram

__all__ = [
    "plotseis",
    "relative_time_array",
    "time_array",
    "unix_time_array",
]


def time_array(seismogram: Seismogram) -> npt.NDArray[np.floating]:
    """Create an array containing Matplotlib dates.

    Args:
        seismogram: Seismogram object.

    Returns:
        Array containing the Matplotlib dates (number of days since the
        Matplotlib epoch, default 1970-01-01) of each point in the
        seismogram data.

    Examples:
        ```python
        >>> from pysmo.tools.plotutils import time_array
        >>> from pysmo.classes import SAC
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> seis_data = seis.data
        >>> seis_times = time_array(seis)
        >>> for t, v in zip(seis_times, seis_data):
        ...     print(t,v)
        ...
        14667.280625804839 -47201.0
        14667.280626383543 -47361.0
        14667.280626962245 -47511.0
        14667.28062754095 -47666.0
        14667.280628119654 -47826.0
        14667.280628698358 -47993.0
        ...
        >>>
        ```
    """
    start = mdates.date2num(seismogram.begin_time)
    end = mdates.date2num(seismogram.end_time)
    return np.linspace(start, end, len(seismogram.data))


def unix_time_array(seismogram: Seismogram) -> npt.NDArray[np.floating]:
    """Create an array containing unix epoch dates.

    Args:
        seismogram: Seismogram object.

    Returns:
        Array containing the unix epoch times (number of seconds since 1970)
        of each point in the seismogram data.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotutils import unix_time_array
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> seis_data = seis.data
        >>> seis_times = unix_time_array(seis)
        >>> for t, v in zip(seis_times, seis_data):
        ...     print(t,v)
        ...
        1267253046.069538 -47201.0
        1267253046.119538 -47361.0
        1267253046.169538 -47511.0
        1267253046.2195382 -47666.0
        1267253046.2695382 -47826.0
        1267253046.319538 -47993.0
        ...
        >>>
        ```
    """
    start = seismogram.begin_time.timestamp()
    end = seismogram.end_time.timestamp()
    return np.linspace(start, end, len(seismogram.data))


def relative_time_array(
    seismogram: Seismogram, reference: pd.Timestamp
) -> npt.NDArray[np.floating]:
    """Create an array of elapsed seconds relative to a reference time.

    Args:
        seismogram: Seismogram object.
        reference: Reference time.

    Returns:
        Array containing the elapsed time (in seconds) of each point in the
        seismogram data, relative to `reference`. Values are negative for
        points before `reference`.

    Examples:
        ```python
        >>> from pysmo.tools.plotutils import relative_time_array
        >>> from pysmo.classes import SAC
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> reference = seis.begin_time + (seis.end_time - seis.begin_time) / 2
        >>> rel_times = relative_time_array(seis, reference)
        >>> bool(rel_times[0] < 0 < rel_times[-1])
        True
        >>>
        ```
    """
    start = (seismogram.begin_time - reference).total_seconds()
    end = (seismogram.end_time - reference).total_seconds()
    return np.linspace(start, end, len(seismogram.data))


def plotseis(
    *seismograms: Seismogram,
    outfile: str = "",
    showfig: bool = True,
    title: str = "",
    **kwargs: Any,
) -> matplotlib.figure.Figure:
    """Plot Seismogram objects.

    Args:
        seismograms: One or more seismogram objects. If a 'label' attribute is
            found it will be used to label the trace in the plot.
        outfile: Optionally save figure to this filename.
        showfig: Display figure.
        title: Optionally set figure title.
        kwargs: Optional keyword arguments passed directly to `matplotlib.pyplot.plot`.

    Returns:
        The matplotlib [`Figure`][matplotlib.figure.Figure] containing the plot.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.plotutils import plotseis
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> fig = plotseis(seis)
        >>>
        ```
    """
    fig = plt.figure()
    any_labelled = False
    for seis in seismograms:
        time = time_array(seis)
        plot_kwargs = dict(kwargs)
        if "label" not in plot_kwargs:
            plot_kwargs["label"] = getattr(seis, "label", None)
        any_labelled = any_labelled or bool(plot_kwargs["label"])
        plt.plot(time, seis.data, scalex=True, scaley=True, **plot_kwargs)
    plt.xlabel("Time")
    plt.gcf().autofmt_xdate()
    fmt = mdates.DateFormatter("%H:%M:%S")
    plt.gca().xaxis.set_major_formatter(fmt)
    if not title:
        left, _ = plt.xlim()
        title = mdates.num2date(left).strftime("%Y-%m-%d %H:%M:%S")
    plt.title(title)
    if any_labelled:
        plt.legend()
    if outfile:
        plt.savefig(outfile)
    if showfig:
        plt.show()
    return fig
