"""
Iterative Cross-Correlation and Stack (ICCS).

Warning:
    This module is being developed alongside a complete rewrite of
    [AIMBAT](https://github.com/pysmo/aimbat). Expect major changes until
    the rewrite is complete.

The ICCS[^1] method is an iterative algorithm to rapidly determine the best
fitting delay times between an arbitrary number of seismograms. In each
iteration, individual seismograms are cross-correlated with the stack of all
input seismograms to improve the previous (or initial) phase arrival picks.

The [`iccs`][pysmo.tools.iccs] module requires seismograms containing extra
attributes specific to the ICCS method. Hence it provides a protocol class
([`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram]) and corresponding Mini
class ([`MiniICCSSeismogram`][pysmo.tools.iccs.MiniICCSSeismogram]) for that
purpose.

Note that the results of ICCS are not as accurate as those of the better
known MCCC[^2] method. However, as MCCC requires carefully chosen input
picks and time windows, ICCS can be used to prepare data for a successful
MCCC run.

[^1]: Lou, X., et al. “AIMBAT: A Python/Matplotlib Tool for Measuring
    Teleseismic Arrival Times.” Seismological Research Letters, vol. 84,
    no. 1, Jan. 2013, pp. 85–93, https://doi.org/10.1785/0220120033.
[^2]: VanDecar, J. C., and R. S. Crosson. “Determination of Teleseismic
    Relative Phase Arrival Times Using Multi-Channel Cross-Correlation and
    Least Squares.” Bulletin of the Seismological Society of America,
    vol. 80, no. 1, Feb. 1990, pp. 150–69,
    https://doi.org/10.1785/BSSA0800010150.

Examples:
    We begin with a set of SAC files of the same event, recorded at different
    stations. All files have a preliminary phase arrival estimate saved in the
    `T0` SAC header, so we can use these files to create instances of the
    [`MiniICCSSeismogram`][pysmo.tools.iccs.MiniICCSSeismogram] class for use
    with the [`ICCS`][pysmo.tools.iccs.ICCS] class:

    ```python
    >>> from glob import glob
    >>> from pysmo.classes import SAC
    >>> from pysmo.functions import clone_to_mini
    >>> from pysmo.tools.iccs import MiniICCSSeismogram
    >>>
    >>> (sacfiles := sorted(glob("iccs-example/*.bhz")))
    ['iccs-example/ci_chf.bhz', 'iccs-example/ci_dan.bhz', ...]
    >>>
    >>> iccs_seismograms = []
    >>> for index, sacfile in enumerate(sacfiles):
    ...     sac = SAC.from_file(sacfile)
    ...     update = {"t0": sac.timestamps.t0}
    ...     iccs_seismogram = clone_to_mini(MiniICCSSeismogram, sac.seismogram, update=update)
    ...     iccs_seismograms.append(iccs_seismogram)
    ...
    >>>
    ```

    To better illustrate the different modes of running the ICCS algorithm, we
    modify the data and picks in the seismograms to make them **worse** than
    they actually are:

    ```python
    >>> from datetime import timedelta
    >>> from copy import deepcopy
    >>> import numpy as np
    >>>
    >>> # change the sign of the data in the first seismogram
    >>> iccs_seismograms[0].data *= -1
    >>>
    >>> # move the initial pick 2 seconds earlier in second seismogram
    >>> iccs_seismograms[1].t0 += timedelta(seconds=-2)
    >>>
    >>> # move the initial pick 2 seconds later in third seismogram
    >>> iccs_seismograms[2].t0 += timedelta(seconds=2)
    >>>
    >>> # create a seismogram with completely random data
    >>> iccs_random: MiniICCSSeismogram = deepcopy(iccs_seismograms[-1])
    >>> iccs_random.data = np.random.rand(len(iccs_random))
    >>> iccs_seismograms.append(iccs_random)
    >>>
    ```

    We can now create an instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class
    and plot the initial stack together with the input seismograms:

    ```python
    >>> from pysmo.tools.iccs import ICCS, plotstack
    >>> iccs = ICCS(iccs_seismograms)
    >>> _ = plotstack(iccs)
    >>>
    ```

    ![initial stack](/examples/tools/iccs/stack_initial.png#only-light){ loading=lazy }
    ![initial stack](/examples/tools/iccs/stack_initial_dark.png#only-dark){ loading=lazy }

    The phase emergance is not visible in the stack, and the (absolute)
    correlation coefficents of the the seismograms are not very high. This
    shows the initial picks are not very good and/or that the data are of low
    quality. To run the ICCS algorithm, we simply call (execute) the ICCS
    instance:

    ```python
    >>> convergence_list = iccs()  # this runs the ICCS algorithm and returns
    >>>                            # a list of the convergence value after each
    >>>                            # iteration.
    >>> _ = plotstack(iccs)
    >>>
    ```
    ![initial stack](/examples/tools/iccs/stack_first_run.png#only-light){ loading=lazy }
    ![initial stack](/examples/tools/iccs/stack_first_run_dark.png#only-dark){ loading=lazy }

    Despite of the random noise seismogram, the phase arrival is now visible in
    the stack. Seismograms with low correlation coefficients can automatically
    be deselected from the calculations by running ICCS again with
    `autoselect=True`:


    ```python
    >>> _ = iccs(autoselect=True)
    >>> _ = plotstack(iccs)
    >>>
    ```

    ![initial stack](/examples/tools/iccs/stack_autoselect.png#only-light){ loading=lazy }
    ![initial stack](/examples/tools/iccs/stack_autoselect_dark.png#only-dark){ loading=lazy }

    Seisimograms that fit better with their polarity reversed can be flipped
    automatically by setting `autoflip=True`:

    ```python
    >>> _ = iccs(autoflip=True)
    >>> _ = plotstack(iccs)
    >>>
    ```

    ![initial stack](/examples/tools/iccs/stack_autoflip.png#only-light){ loading=lazy }
    ![initial stack](/examples/tools/iccs/stack_autoflip_dark.png#only-dark){ loading=lazy }
"""

from ._functions import plotstack
from ._iccs import ICCS
from ._types import MiniICCSSeismogram, ICCSSeismogram

__all__ = ["plotstack", "ICCS", "ICCSSeismogram", "MiniICCSSeismogram"]
