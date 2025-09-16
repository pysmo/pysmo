"""The ICCS class and functions used within the class."""

from ._types import ICCSSeismogram
from pysmo import Seismogram, MiniSeismogram
from pysmo.functions import (
    crop,
    taper,
    detrend,
    normalize,
    clone_to_mini,
    resample,
    pad,
)
from pysmo.tools.signal import delay
from pysmo.tools.utils import average_datetimes
from datetime import timedelta
from attrs import define, field, validators, Attribute
from typing import Any, Literal
from collections.abc import Sequence
from scipy.stats.mstats import pearsonr
from numpy.linalg import norm
from functools import partial
from concurrent.futures import ProcessPoolExecutor, Future
import warnings
import numpy as np
import numpy.typing as npt


__all__ = ["ICCS"]

CONVERGENCE_METHOD = Literal["corrcoef", "change"]


def _clear_cache_on_update(instance: "ICCS", attribute: Attribute, value: Any) -> None:
    """Validator that causes cached attributes to be cleared."""
    if getattr(instance, attribute.name) != value:
        instance._clear_caches()


def _validate_window_pre(
    instance: "ICCS", attribute: Attribute, value: timedelta
) -> None:
    """Ensure window_pre is with the seismogram limits for all selected seismograms."""
    if not all(
        s.begin_time - value <= (s.t1 or s.t0) for s in instance.seismograms if s.select
    ):
        raise ValueError("window_pre is too low for one or more seismograms.")


def _validate_window_post(
    instance: "ICCS", attribute: Attribute, value: timedelta
) -> None:
    """Ensure window_post is with the seismogram limits for all selected seismograms."""
    if not all(
        (s.t1 or s.t0) + value <= s.end_time for s in instance.seismograms if s.select
    ):
        raise ValueError("window_post is too high for one or more seismograms.")


@define(slots=True)
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
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.iccs import MiniICCSSeismogram
        >>> from pathlib import Path
        >>>
        >>> sacfiles = sorted(Path("iccs-example/").glob("*.bhz"))
        >>>
        >>> seismograms = []
        >>> for sacfile in sacfiles:
        ...     sac = SAC.from_file(sacfile)
        ...     update = {"t0": sac.timestamps.t0}
        ...     iccs_seismogram = clone_to_mini(MiniICCSSeismogram, sac.seismogram, update=update)
        ...     seismograms.append(iccs_seismogram)
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
        >>> seismograms[0].data *= -1
        >>>
        >>> # move the initial pick 2 seconds earlier in second seismogram
        >>> seismograms[1].t0 += timedelta(seconds=-2)
        >>>
        >>> # move the initial pick 2 seconds later in third seismogram
        >>> seismograms[2].t0 += timedelta(seconds=2)
        >>>
        >>> # create a seismogram with completely random data
        >>> iccs_random: MiniICCSSeismogram = deepcopy(seismograms[-1])
        >>> np.random.seed(42)  # set this for consistent results during testing
        >>> iccs_random.data = np.random.rand(len(iccs_random))
        >>> seismograms.append(iccs_random)
        >>>
        ```

        We can now create an instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class
        and plot the initial stack together with the input seismograms:

        ```python
        >>> from pysmo.tools.iccs import ICCS, plotstack
        >>> iccs = ICCS(seismograms)
        >>> plotstack(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     import matplotlib.pyplot as plt
        ...     plt.close()
        ...     plt.style.use("dark_background")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_initial-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_initial.png", transparent=True)
        >>>
        ```
        -->

        ![Initial stack](../../../examples/figures/iccs_stack_initial.png#only-light){ loading=lazy }
        ![Initial stack](../../../examples/figures/iccs_stack_initial-dark.png#only-dark){ loading=lazy }

        The phase emergance is not visible in the stack, and the (absolute)
        correlation coefficents of the the seismograms are not very high. This
        shows the initial picks are not very good and/or that the data are of low
        quality. To run the ICCS algorithm, we simply call (execute) the ICCS
        instance:

        ```python
        >>> convergence_list = iccs()  # this runs the ICCS algorithm and returns
        >>>                            # a list of the convergence value after each
        >>>                            # iteration.
        >>> plotstack(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     import matplotlib.pyplot as plt
        ...     plt.close()
        ...     plt.style.use("dark_background")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_first_run-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_first_run.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after first run](../../../examples/figures/iccs_stack_first_run.png#only-light){ loading=lazy }
        ![Stack after first run](../../../examples/figures/iccs_stack_first_run-dark.png#only-dark){ loading=lazy }

        Despite of the random noise seismogram, the phase arrival is now visible in
        the stack. Seismograms with low correlation coefficients can automatically
        be deselected from the calculations by running ICCS again with
        `autoselect=True`:


        ```python
        >>> _ = iccs(autoselect=True)
        >>> plotstack(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     import matplotlib.pyplot as plt
        ...     plt.close()
        ...     plt.style.use("dark_background")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoselect-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoselect.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after run with autoselect](../../../examples/figures/iccs_stack_autoselect.png#only-light){ loading=lazy }
        ![Stack after run with autoselect](../../../examples/figures/iccs_stack_autoselect-dark.png#only-dark){ loading=lazy }


        Seismograms that fit better with their polarity reversed can be flipped
        automatically by setting `autoflip=True`:

        ```python
        >>> _ = iccs(autoflip=True)
        >>> plotstack(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     import matplotlib.pyplot as plt
        ...     plt.close()
        ...     plt.style.use("dark_background")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoflip-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plotstack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoflip.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after run with autoflip](../../../examples/figures/iccs_stack_autoflip.png#only-light){ loading=lazy }
        ![Stack after run with autoflip](../../../examples/figures/iccs_stack_autoflip-dark.png#only-dark){ loading=lazy }


        To further improve results, you can interactively update the picks and
        the time window using [`stack_pick`][pysmo.tools.iccs.stack_pick] and
        [`stack_tw_pick`][pysmo.tools.iccs.stack_tw_pick], respectively, and
        then run the ICCS algorithm again.
    """

    seismograms: Sequence[ICCSSeismogram] = field(
        factory=lambda: list[ICCSSeismogram](), validator=_clear_cache_on_update
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
        validator=[
            validators.lt(timedelta(seconds=0)),
            _validate_window_pre,
            _clear_cache_on_update,
        ],
    )
    """Begining of the time window relative to the pick."""

    window_post: timedelta = field(
        default=timedelta(seconds=10),
        validator=[
            validators.gt(timedelta(seconds=0)),
            _validate_window_post,
            _clear_cache_on_update,
        ],
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

    min_ccnorm: np.floating | float = 0.5
    """Minimum normalised cross-correlation coefficient for seismograms.

    When the ICCS algorithm is [executed][pysmo.tools.iccs.ICCS.__call__],
    the cross-correlation coefficient for each seismogram is calculated after
    each iteration. If `autoselect` is set to `True`, the
    [`select`][pysmo.tools.iccs.ICCSSeismogram.select] attribute of seismograms
    with with correlation coefficients below this value is set to `False`, and
    they are no longer used for the [`stack`][pysmo.tools.iccs.ICCS.stack].
    """

    # The following attributes are cached to prevent unnecessary processing.
    # Setting the caches to None will force a new calculation when they are
    # requested.
    _seismograms_prepared: list[MiniSeismogram] | None = field(init=False)
    _seismograms_for_plotting: list[MiniSeismogram] | None = field(init=False)
    _seismograms_ccnorm: list[float] | None = field(init=False)
    _stack: MiniSeismogram | None = field(init=False)
    _stack_for_plotting: MiniSeismogram | None = field(init=False)
    _valid_pick_range: tuple[timedelta, timedelta] | None = field(init=False)
    _valid_time_window_range: tuple[timedelta, timedelta] | None = field(init=False)

    def __attrs_post_init__(self) -> None:
        self._clear_caches()

    def _clear_caches(self) -> None:
        """Clear all cached attributes."""
        self._seismograms_prepared = None
        self._seismograms_for_plotting = None
        self._seismograms_ccnorm = None
        self._stack = None
        self._stack_for_plotting = None
        self._valid_pick_range = None
        self._valid_time_window_range = None

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
        """Returns the windowed, detrended, normalised, and optionally flipped seismograms."""

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
        """Returns the stacked seismograms ([`seismograms_prepared`][pysmo.tools.iccs.ICCS.seismograms_prepared]).

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
        """Returns the stacked seismograms ([`seismograms_for_plotting`][pysmo.tools.iccs.ICCS.seismograms_for_plotting]).

        Returns:
            Stacked input seismograms.
        """
        if self._stack_for_plotting is not None:
            return self._stack_for_plotting

        self._stack_for_plotting = _create_stack(
            self.seismograms_for_plotting, self.seismograms
        )
        return self._stack_for_plotting

    def validate_pick(self, pick: timedelta) -> bool:
        """Check if a new pick is valid.

        This checks if a new manual pick is valid for all selected seismograms.

        Parameters:
            pick: New pick to validate.

        Returns:
            Whether the new pick is valid.
        """

        # first calculate valid pick range if not done yet
        if self._valid_pick_range is None:
            self._valid_pick_range = _calc_valid_pick_range(self)

        if self._valid_pick_range[0] <= pick <= self._valid_pick_range[1]:
            return True
        return False

    def validate_time_window(
        self, window_pre: timedelta, window_post: timedelta
    ) -> bool:
        """Check if a new time window (relative to pick) is valid.

        Parameters:
            window_pre: New window start time to validate.
            window_post: New window end time to validate.

        Returns:
            Whether the new time window is valid.
        """

        if window_pre >= window_post:
            return False

        if window_pre > -self.stack.delta:
            return False

        if window_post < self.stack.delta:
            return False

        # Calculate valid time window range if not done yet
        if self._valid_time_window_range is None:
            self._valid_time_window_range = _calc_valid_time_window_range(self)

        if (
            self._valid_time_window_range[0] <= window_pre
            and window_post <= self._valid_time_window_range[1]
        ):
            return True
        return False

    def __call__(
        self,
        autoflip: bool = False,
        autoselect: bool = False,
        convergence_limit: float = 10e-6,
        convergence_method: CONVERGENCE_METHOD = "corrcoef",
        max_iter: int = 10,
        max_shift: timedelta | None = None,
        parallel: bool = False,
    ) -> npt.NDArray:
        """Run the iccs algorithm.

        Parameters:
            autoflip: Automatically toggle [`flip`][pysmo.tools.iccs.ICCSSeismogram.flip] attribute of seismograms.
            autoselect: Automatically set `select` attribute to `False` for poor quality seismograms.
            convergence_limit: Convergence limit at which the algorithm stops.
            convergence_method: Method to calculate convergence criterion.
            max_iter: Maximum number of iterations.
            max_shift: Maximum shift in seconds (see [`delay()`][pysmo.tools.signal.delay]).
            parallel: Whether to use parallel processing. Setting this to `True`
                will perform the cross-correlation calculations in parallel
                using [`ProcessPoolExecutor`][concurrent.futures.ProcessPoolExecutor].
                In most cases this will *not* be faster.

        Returns:
            convergence: Array of convergence criterion values.
        """
        convergence_list = []

        for _ in range(max_iter):
            prev_stack = clone_to_mini(MiniSeismogram, self.stack)

            if parallel:
                with ProcessPoolExecutor() as executor:
                    for prepared_seismogram, seismogram in zip(
                        self.seismograms_prepared, self.seismograms
                    ):
                        future = executor.submit(
                            delay,
                            self.stack,
                            prepared_seismogram,
                            max_shift=max_shift,
                            abs_max=autoflip,
                        )
                        future.add_done_callback(
                            partial(
                                _update_seismogram_fn,
                                seismogram,
                                autoflip,
                                autoselect,
                                self.min_ccnorm,
                                (self.window_pre, self.window_post),
                            )
                        )
            else:
                for prepared_seismogram, seismogram in zip(
                    self.seismograms_prepared, self.seismograms
                ):
                    _delay, _ccnorm = delay(
                        self.stack,
                        prepared_seismogram,
                        max_shift=max_shift,
                        abs_max=autoflip,
                    )

                    _update_seismogram(
                        _delay,
                        _ccnorm,
                        seismogram,
                        autoflip,
                        autoselect,
                        self.min_ccnorm,
                        (self.window_pre, self.window_post),
                    )

            self._clear_caches()

            convergence = _calc_convergence(self.stack, prev_stack, convergence_method)
            convergence_list.append(convergence)
            if convergence <= convergence_limit:
                break

        return np.array(convergence_list)


def _prepare_seismograms(
    seismograms: Sequence[ICCSSeismogram],
    window_pre: timedelta,
    window_post: timedelta,
    taper_width: timedelta | float,
    prep_for_plotting: bool = False,
    plot_padding: None | timedelta = None,
) -> list[MiniSeismogram]:
    return_seismograms: list[MiniSeismogram] = []

    min_delta = min((s.delta for s in seismograms))

    for seismogram in seismograms:
        pick = seismogram.t1 or seismogram.t0
        window_start = pick + window_pre
        window_end = pick + window_post
        prepared_seismogram = clone_to_mini(MiniSeismogram, seismogram)
        resample(prepared_seismogram, min_delta)

        if prep_for_plotting:
            if plot_padding is None:
                raise ValueError(
                    "if prep_for_plotting is True, plot_padding must also be specified."
                )

            plot_window_start = window_start - plot_padding
            plot_window_end = window_end + plot_padding

            if (
                plot_window_start < seismogram.begin_time
                or plot_window_end > seismogram.end_time
            ):
                pad(
                    prepared_seismogram,
                    plot_window_start,
                    plot_window_end,
                    mode="linear_ramp",
                    end_values=(0, 0),
                )

            crop(prepared_seismogram, plot_window_start, plot_window_end)
            detrend(prepared_seismogram)
            normalize(prepared_seismogram, window_start, window_end)
        else:
            crop(prepared_seismogram, window_start, window_end)
            detrend(prepared_seismogram)
            taper(prepared_seismogram, taper_width)
            normalize(prepared_seismogram)
        if seismogram.flip is True:
            prepared_seismogram.data *= -1
        return_seismograms.append(prepared_seismogram)

    # If all seismograms must have the same length, return them now.
    if len(lengths := set(len(s) for s in return_seismograms)) == 1:
        return return_seismograms

    # Shorten seismograms if necessary and return.
    for s in return_seismograms:
        s.data = s.data[: min(lengths)]
    return return_seismograms


def _update_seismogram(
    delay: timedelta,
    ccnorm: float,
    seismogram: ICCSSeismogram,
    autoflip: bool,
    autoselect: bool,
    min_ccnorm_for_autoselect: np.floating | float,
    current_window: tuple[timedelta, timedelta],
) -> None:
    """Update ICCSSeismogram attributes based on cross-correlation results."""

    if autoflip and ccnorm < 0:
        seismogram.flip = not seismogram.flip
        ccnorm = abs(ccnorm)

    if autoselect:
        if ccnorm < min_ccnorm_for_autoselect:
            seismogram.select = False
        # TODO: Should we also set to True?

    updated_t1 = (seismogram.t1 or seismogram.t0) + delay
    limit_pre = seismogram.begin_time - current_window[0]
    limit_post = seismogram.end_time - current_window[1]

    if not limit_pre <= updated_t1 <= limit_post:
        warnings.warn(
            f"refusing to update t1 for {seismogram=}. Would move out of limits - consider reducing window size."
        )
        return

    seismogram.t1 = updated_t1


def _update_seismogram_fn(
    seismogram: ICCSSeismogram,
    autoflip: bool,
    autoselect: bool,
    min_ccnorm_for_autoselect: np.floating | float,
    current_window: tuple[timedelta, timedelta],
    fn: Future[tuple[timedelta, float]],
) -> None:
    """Update ICCSSeismogram attributes based on multi-threaded cross-correlation results."""
    delay, ccnorm = fn.result()
    _update_seismogram(
        delay,
        ccnorm,
        seismogram,
        autoflip,
        autoselect,
        min_ccnorm_for_autoselect,
        current_window,
    )


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
    raise ValueError(f"Unknown convergence method: {method}.")


def _calc_valid_pick_range(iccs: ICCS) -> tuple[timedelta, timedelta]:
    """Calculate the valid range for updating pick."""

    min_pick = max(
        s.begin_time - (s.t1 or s.t0) - iccs.window_pre
        for s in iccs.seismograms
        if s.select
    )
    max_pick = min(
        s.end_time - (s.t1 or s.t0) - iccs.window_post
        for s in iccs.seismograms
        if s.select
    )

    return min_pick, max_pick


def _calc_valid_time_window_range(iccs: ICCS) -> tuple[timedelta, timedelta]:
    """Calculate the valid range for updating time window."""

    min_window_pre = max(
        s.begin_time - (s.t1 or s.t0) for s in iccs.seismograms if s.select
    )
    max_window_post = min(
        s.end_time - (s.t1 or s.t0) for s in iccs.seismograms if s.select
    )

    return min_window_pre, max_window_post
