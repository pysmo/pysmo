import numpy as np
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
from pysmo import Seismogram


def plotseis(*seismograms: Seismogram, outfile: str = "", showfig: bool = True,
             title: str = "", **kwargs: dict) -> plt.FigureBase:
    """
    Plots Seismogram objects.

    :param seismograms: One or more seismogram objects. If a 'label' attribute is found
                        it will be used to label the trace in the plot.
    :type seismograms: pysmo.Seismogram
    :param outfile: Optionally save figure to this filename.
    :type outfile: str
    :param showfig: Display figure.
    :type showfig: bool
    :param title: Optionally set figure title.
    :type title: str
    :param kwargs: Optionally add kwargs to pass to the plot command
    :type kwargs: dict

    Example usage::

        >>> from pysmo import SAC, plotseis
        >>> seis = SAC.from_file('sacfile.sac').Seismogram
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
