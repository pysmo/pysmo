"""The ICCS class and functions used within the class."""

from ._types import ICCSSeismogram
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import crop, taper, detrend, normalize, clone_to_mini
from pysmo.tools.signal import delay
from pysmo.tools.utils import average_datetimes
from datetime import timedelta
from attrs import define, field, validators, Attribute
from typing import Any, Literal
from collections.abc import Sequence
from scipy.stats.mstats import pearsonr
from numpy.linalg import norm
from copy import deepcopy
import numpy as np
import numpy.typing as npt


__all__ = ["ICCS"]

CONVERGENCE_METHOD = Literal["corrcoef", "change"]


def _clear_cache_on_update(instance: "ICCS", attribute: Attribute, value: Any) -> None:
    """Validator that causes cached attributes to be cleared."""
    if getattr(instance, attribute.name) != value:
        instance._clear_caches()


def _prepare_seismograms(
    seismograms: Sequence[ICCSSeismogram],
    window_pre: timedelta,
    window_post: timedelta,
    taper_width: timedelta | float,
    prep_for_plotting: bool = False,
    plot_padding: None | timedelta = None,
) -> list[MiniSeismogram]:
    return_seismograms = []
    for seismogram in seismograms:
        pick = seismogram.t1 or seismogram.t0
        window_start = pick + window_pre
        window_end = pick + window_post
        return_seismogram = clone_to_mini(MiniSeismogram, seismogram)
        if prep_for_plotting:
            if plot_padding is None:
                raise ValueError("plot_padding must be specified")
            crop(
                return_seismogram,
                window_start - plot_padding,
                window_end + plot_padding,
            )
            detrend(return_seismogram)
        else:
            crop(return_seismogram, window_start, window_end)
            detrend(return_seismogram)
            taper(return_seismogram, taper_width)
        normalize(return_seismogram, window_start, window_end)
        if seismogram.flip is True:
            return_seismogram.data *= -1
        return_seismograms.append(return_seismogram)
    return return_seismograms


def _calc_ccnorms(seismograms: Sequence[Seismogram], stack: Seismogram) -> list[float]:
    ccnorms = [
        float(pearsonr(seismogram.data, stack.data)[0]) for seismogram in seismograms
    ]
    return ccnorms


def _create_stack(
    prepared_seismograms: Sequence[Seismogram], seismograms: Sequence[ICCSSeismogram]
) -> MiniSeismogram:
    begin_time = average_datetimes(
        [p.begin_time for p, s in zip(prepared_seismograms, seismograms) if s.select]
    )
    delta = prepared_seismograms[0].delta
    data = np.mean(
        np.array(
            [p.data for p, s in zip(prepared_seismograms, seismograms) if s.select]
        ),
        axis=0,
    )
    return MiniSeismogram(begin_time=begin_time, delta=delta, data=data)


def _calc_convergence(
    current_stack: Seismogram,
    prev_stack: Seismogram,
    method: CONVERGENCE_METHOD,
) -> float:
    """Calcuate criterion of convergence.

    This function calculates a criterion of convergence based on the current and
    previous stack using one of the following methods:

    - Convergence by correlation coefficient.
    - Convergence by change of stack

    Parameters:
        current_stack: Current stack.
        prev_stack: Stack from last iteration.
        method: Method of convergence criterion calculation.
    """
    if method == "corrcoef":
        covr, _ = pearsonr(current_stack.data, prev_stack.data)
        return 1 - float(covr)
    elif method == "change":
        return float(
            norm(current_stack.data - prev_stack.data, 1)
            / norm(current_stack.data, 2)
            / len(current_stack)
        )


@define
class ICCS:
    """Class to store a list of [`ICCSSeismograms`][pysmo.tools.iccs.ICCSSeismogram] and run the ICCS algorithm.

    The [`ICCS`][pysmo.tools.iccs.ICCS] class serves as a container to store a
    list of seismograms (typically recordings of the same event at different
    stations), and to then run the ICCS algorithm when an instance of this
    class is called. Processing parameters that are common to all seismograms
    are stored as attributes (e.g. time window limits).

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
        >>> sacfiles = sorted(glob("iccs-example/*.bhz"))
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
        >>> _ = plotstack(iccs, padded=False)
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
        >>> _ = plotstack(iccs, padded=False)
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
        >>> _ = plotstack(iccs, padded=False)
        >>>
        ```

        ![initial stack](/examples/tools/iccs/stack_autoselect.png#only-light){ loading=lazy }
        ![initial stack](/examples/tools/iccs/stack_autoselect_dark.png#only-dark){ loading=lazy }

        Seismograms that fit better with their polarity reversed can be flipped
        automatically by setting `autoflip=True`:

        ```python
        >>> _ = iccs(autoflip=True)
        >>> _ = plotstack(iccs, padded=False)
        >>>
        ```

        ![initial stack](/examples/tools/iccs/stack_autoflip.png#only-light){ loading=lazy }
        ![initial stack](/examples/tools/iccs/stack_autoflip_dark.png#only-dark){ loading=lazy }
    """

    seismograms: Sequence[ICCSSeismogram] = field(
        factory=lambda: list(), validator=_clear_cache_on_update
    )
    """Input seismograms.

    These seismograms provide the input data for ICCS. They are used to store
    processing parameters and create shorter seismograms (based on pick and
    time window) that are then used for cross-correlation. The shorter
    seismograms are created on the fly and then cached within an [`ICCS`]
    [pysmo.tools.iccs.ICCS] instance.
    """

    window_pre: timedelta = field(
        default=timedelta(seconds=-10),
        validator=[validators.lt(timedelta(seconds=0)), _clear_cache_on_update],
    )
    """Begining of the time window relative to the pick."""

    window_post: timedelta = field(
        default=timedelta(seconds=10),
        validator=[validators.gt(timedelta(seconds=0)), _clear_cache_on_update],
    )
    """End of the time window relative to the pick."""

    plot_padding: timedelta = field(
        default=timedelta(seconds=10),
        validator=[validators.gt(timedelta(seconds=0)), _clear_cache_on_update],
    )
    """Padding to apply before and after the time window.

    This padding is *not* used for the cross-correlation."""

    taper_width: timedelta | float = field(
        default=0.0, validator=_clear_cache_on_update
    )
    """Taper width.

    Can be either a timedelta or a float - see [`pysmo.functions.taper()`][pysmo.functions.taper]
    for details.
    """

    # Prepared seismograms and stack are cached to prevent unnecessary
    # processing. Setting the caches to None will force a new calculation.
    _seismograms_prepared: list[MiniSeismogram] | None = field(init=False)
    _seismograms_for_plotting: list[MiniSeismogram] | None = field(init=False)
    _seismograms_ccnorm: list[float] | None = field(init=False)
    _stack: MiniSeismogram | None = field(init=False)
    _stack_for_plotting: MiniSeismogram | None = field(init=False)

    def __attrs_post_init__(self) -> None:
        self._clear_caches()

    def _clear_caches(self) -> None:
        """Clear all cached attributes."""
        self._seismograms_prepared = None
        self._seismograms_for_plotting = None
        self._seismograms_ccnorm = None
        self._stack = None
        self._stack_for_plotting = None

    @property
    def seismograms_prepared(self) -> list[MiniSeismogram]:
        """Returns the windowed, detrended, normalised, tapered, and optionally flipped seismograms."""

        if self._seismograms_prepared is None:
            self._seismograms_prepared = _prepare_seismograms(
                self.seismograms,
                self.window_pre,
                self.window_post,
                self.taper_width,
            )

        return self._seismograms_prepared

    @property
    def seismograms_for_plotting(self) -> list[MiniSeismogram]:
        """Returns the windowed, detrended, normalised, tapered, and optionally flipped seismograms."""

        if self._seismograms_for_plotting is None:
            self._seismograms_for_plotting = _prepare_seismograms(
                self.seismograms,
                self.window_pre,
                self.window_post,
                self.taper_width,
                True,
                self.plot_padding,
            )

        return self._seismograms_for_plotting

    @property
    def seismograms_ccnorm(self) -> list[float]:
        """Returns a list of the normalised cross-correlation coefficients."""

        if self._seismograms_ccnorm is None:
            self._seismograms_ccnorm = _calc_ccnorms(
                self.seismograms_prepared, self.stack
            )

        return self._seismograms_ccnorm

    @property
    def stack(self) -> MiniSeismogram:
        """Returns the stacked [`prepared_seismograms`][pysmo.tools.iccs.ICCS.prepared_seismograms].

        The stack is calculated as the average of all seismograms with the
        attribute [`select`][pysmo.tools.iccs.ICCSSeismogram.select] set to
        [`True`][True]. The [`begin_time`][pysmo.MiniSeismogram.begin_time] of
        the returned stack is the average of the [`begin_time`]
        [pysmo.tools.iccs.ICCSSeismogram.begin_time] of the input seismograms.

        Returns:
            Stacked input seismograms.
        """
        if self._stack is not None:
            return self._stack

        self._stack = _create_stack(self.seismograms_prepared, self.seismograms)
        return self._stack

    @property
    def stack_for_plotting(self) -> MiniSeismogram:
        """Returns the stacked [`prepared_seismograms`][pysmo.tools.iccs.ICCS.prepared_seismograms].

        Returns:
            Stacked input seismograms.
        """
        if self._stack_for_plotting is not None:
            return self._stack_for_plotting

        self._stack_for_plotting = _create_stack(
            self.seismograms_for_plotting, self.seismograms
        )
        return self._stack_for_plotting

    def __call__(
        self,
        autoflip: bool = False,
        autoselect: bool = False,
        convergence_limit: float = 10e-5,
        convergence_method: CONVERGENCE_METHOD = "corrcoef",
        max_iter: int = 10,
        max_shift: timedelta | None = None,
        min_ccnorm: float = 0.5,
    ) -> npt.NDArray:
        """Run the iccs algorithm.

        Parameters:
            autoflip: Automatically toggle [`flip`][pysmo.tools.iccs.ICCSSeismogram.flip] attribute of seismograms.
            autoselect: Automatically set `select` attribute to `False` for poor quality seismograms.
            max_iter: Maximum number of iterations.
            max_shift: Maximum shift in seconds (see [`delay()`][pysmo.tools.signal.delay]).
            min_ccnorm: Minimum normalised cross-correlation coefficient.
                When `autoselect` is `True`, seismograms with correlation
                coefficients below this value are set to `select=False`.

        Returns:
            convergence: Array of convergence criterion values.
        """
        convergence_list = []

        for _ in range(max_iter):
            prev_stack = deepcopy(self.stack)
            for prepared_seismogram, seismogram in zip(
                self.seismograms_prepared, self.seismograms
            ):
                _delay, _ccnorm = delay(
                    self.stack,
                    prepared_seismogram,
                    max_shift=max_shift,
                    abs_max=autoflip,
                )

                if autoflip and _ccnorm < 0:
                    seismogram.flip = not seismogram.flip
                    _ccnorm = abs(_ccnorm)

                if autoselect:
                    if _ccnorm < min_ccnorm:
                        seismogram.select = False
                    # TODO: Should we also set to True?

                seismogram.t1 = (seismogram.t1 or seismogram.t0) + _delay

            self._clear_caches()

            convergence = _calc_convergence(self.stack, prev_stack, convergence_method)
            convergence_list.append(convergence)
            if convergence <= convergence_limit:
                break

        return np.array(convergence_list)
