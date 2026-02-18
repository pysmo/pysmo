"""The ICCS class and functions used within the class."""

from beartype import beartype
from ._types import ICCSSeismogram, ConvergenceMethod
from ._defaults import ICCS_DEFAULTS
from pysmo import Seismogram, MiniSeismogram
from pysmo.typing import (
    NonNegativeNumber,
    NonNegativeTimedelta64,
)
from pysmo.functions import (
    crop,
    detrend,
    normalize,
    clone_to_mini,
    resample,
    pad,
    window,
)
from pysmo.tools.signal import bandpass, multi_delay
from pysmo.tools.utils import average_datetimes, pearson_matrix_vector, to_seconds
from attrs import define, field, validators, Attribute
from typing import Any
from collections.abc import Sequence
from scipy.stats.mstats import pearsonr
from numpy.linalg import norm
import warnings
import numpy as np

__all__ = ["ICCS"]


def _clear_cache_on_update(instance: "ICCS", attribute: Attribute, value: Any) -> None:
    """Validator that causes cached attributes to be cleared."""
    if getattr(instance, attribute.name) != value:
        instance._clear_caches()


def _validate_window_pre(
    instance: "ICCS", attribute: Attribute, value: np.timedelta64
) -> None:
    """Ensure window_pre is with the seismogram limits for all selected seismograms."""
    if not all(
        s.begin_time - value <= (s.t1 or s.t0) for s in instance.seismograms if s.select
    ):
        raise ValueError("window_pre is too low for one or more seismograms.")


def _validate_window_post(
    instance: "ICCS", attribute: Attribute, value: np.timedelta64
) -> None:
    """Ensure window_post is with the seismogram limits for all selected seismograms."""
    if not all(
        (s.t1 or s.t0) + value <= s.end_time for s in instance.seismograms if s.select
    ):
        raise ValueError("window_post is too high for one or more seismograms.")


@define(slots=True)
class _EphemeralSeismogram(Seismogram):
    """A Seismogram class used internally in ICCS to store the prepared seismograms.

    This class is not intended for use outside of the ICCS class, and is not
    exposed in the public API. It is used to store the prepared seismograms
    (i.e. the seismograms that are cropped, tapered, and normalised based on
    the current pick and time window) for use in the cross-correlation and
    stacking. The data in these seismograms are modified on the fly when the
    picks and time windows are updated, but they are not intended to be modified
    directly by users.
    """

    parent_seismogram: ICCSSeismogram
    """Reference to the parent ICCSSeismogram from which this ephemeral seismogram is derived."""

    begin_time: np.datetime64 = field(init=False)
    """Seismogram begin time as numpy datetime64."""

    delta: np.timedelta64 = field(init=False)
    """Seismogram sampling interval as numpy timedelta64."""

    data: np.ndarray = field(init=False)
    """Seismogram data."""

    def __attrs_post_init__(self) -> None:
        self.begin_time = self.parent_seismogram.begin_time
        self.delta = self.parent_seismogram.delta
        self.data = self.parent_seismogram.data.copy()


@beartype
@define(slots=True)
class ICCS:
    """Class to store a list of [`ICCSSeismograms`][pysmo.tools.iccs.ICCSSeismogram] and run the ICCS algorithm.

    The [`ICCS`][pysmo.tools.iccs.ICCS] class serves as a container to store a
    list of seismograms (typically recordings of the same event at different
    stations), and to then run the ICCS algorithm when an instance of this
    class is called. Processing parameters that are common to all seismograms
    are stored as attributes (e.g. time window limits).

    The seismograms stored in an instance are prepared in two distinct ways:

    - **For cross-correlation:** uses [`ramp_width`][pysmo.tools.iccs.ICCS.ramp_width]
      to define how much of the seismogram should be used as *taper* before and
      after the time window of interest. These are the seismograms that form
      the stack and are used in the cross-correlation.
    - **For added context:** uses [`context_width`][pysmo.tools.iccs.ICCS.context_width]
      to define how much of the seismogram should be used as *extra context*
      before and after the time window of interest.
      [`context_width`][pysmo.tools.iccs.ICCS.context_width] should be chosen
      such that a large enough portion of the seismogram is shown to e.g.
      interactively pick new time window boundaries.

    Apart from tapering the two types are processed the same. For performance,
    the prepared seismograms are cached and only calculated on a first call or
    if relevant parameters are updated.

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

        To better illustrate the different modes of running the ICCS algorithm,
        we modify the data and picks in the seismograms to make them **worse**
        than they actually are:

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

        We can now create an instance of the [`ICCS`][pysmo.tools.iccs.ICCS]
        class and plot the initial [`stack`][pysmo.tools.iccs.ICCS.stack] and
        [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]:

        ```python
        >>> from pysmo.tools.iccs import ICCS, plot_stack
        >>> iccs = ICCS(seismograms)
        >>> plot_stack(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_initial-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_initial.png", transparent=True)
        >>>
        ```
        -->

        ![Initial stack](../../../images/tools/iccs/iccs_stack_initial.png#only-light){ loading=lazy }
        ![Initial stack](../../../images/tools/iccs/iccs_stack_initial-dark.png#only-dark){ loading=lazy }

        The phase emergence is not visible in the stack, and the (absolute)
        correlation coefficients of the seismograms are not very high. This
        shows the initial picks are not very good and/or that the data are of
        low quality. To run the ICCS algorithm, we simply call (execute) the
        ICCS instance:

        ```python
        >>> convergence_list = iccs()  # this runs the ICCS algorithm and returns
        >>>                            # a list of the convergence value after each
        >>>                            # iteration.
        >>> plot_stack(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_first_run-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_first_run.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after first run](../../../images/tools/iccs/iccs_stack_first_run.png#only-light){ loading=lazy }
        ![Stack after first run](../../../images/tools/iccs/iccs_stack_first_run-dark.png#only-dark){ loading=lazy }

        Despite the random noise seismogram, the phase arrival is now visible in
        the stack. Seismograms with low correlation coefficients can automatically
        be deselected from the calculations by running ICCS again with
        `autoselect=True`:


        ```python
        >>> _ = iccs(autoselect=True)
        >>> plot_stack(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoselect-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoselect.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after run with autoselect](../../../images/tools/iccs/iccs_stack_autoselect.png#only-light){ loading=lazy }
        ![Stack after run with autoselect](../../../images/tools/iccs/iccs_stack_autoselect-dark.png#only-dark){ loading=lazy }


        Seismograms that fit better with their polarity reversed can be flipped
        automatically by setting `autoflip=True`:

        ```python
        >>> _ = iccs(autoflip=True)
        >>> plot_stack(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoflip-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_stack_autoflip.png", transparent=True)
        >>>
        ```
        -->

        ![Stack after run with autoflip](../../../images/tools/iccs/iccs_stack_autoflip.png#only-light){ loading=lazy }
        ![Stack after run with autoflip](../../../images/tools/iccs/iccs_stack_autoflip-dark.png#only-dark){ loading=lazy }


        To further improve results, you can interactively update the picks,
        time window, and minimum correlation coefficient using
        [`update_pick`][pysmo.tools.iccs.update_pick],
        [`update_timewindow`][pysmo.tools.iccs.update_timewindow], and
        [`update_min_ccnorm`][pysmo.tools.iccs.update_min_ccnorm],
        respectively, and then run the ICCS algorithm again.
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

    window_pre: np.timedelta64 = field(
        default=ICCS_DEFAULTS.window_pre,
        validator=[
            validators.lt(np.timedelta64(0, "us")),
            _validate_window_pre,
            _clear_cache_on_update,
        ],
    )
    """Beginning of the time window relative to the pick as numpy timedelta64."""

    window_post: np.timedelta64 = field(
        default=ICCS_DEFAULTS.window_post,
        validator=[
            validators.gt(np.timedelta64(0, "us")),
            _validate_window_post,
            _clear_cache_on_update,
        ],
    )
    """End of the time window relative to the pick as numpy timedelta64."""

    context_width: np.timedelta64 = field(
        default=ICCS_DEFAULTS.context_width,
        validator=[validators.gt(np.timedelta64(0, "us")), _clear_cache_on_update],
    )
    """Context padding to apply before and after the time window as numpy timedelta64.

    This padding is *not* used for the cross-correlation."""

    ramp_width: NonNegativeTimedelta64 | NonNegativeNumber = field(
        default=ICCS_DEFAULTS.ramp_width, validator=_clear_cache_on_update
    )
    """Width of taper ramp up and down.

    Can be either a numpy timedelta64 or a float - see [`pysmo.functions.window()`][pysmo.functions.window]
    for details.
    """

    bandpass_apply: bool = field(
        default=ICCS_DEFAULTS.bandpass_apply, validator=_clear_cache_on_update
    )
    """Filter seismograms with a bandpass filter before running ICCS.

    Setting this to [`True`][] will apply a
    [`bandpass`][pysmo.tools.signal.bandpass] filter (with `zerophase` set to
    [`True`][]) to the [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]
    and [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms].

    As the [`seismograms`][pysmo.tools.iccs.ICCS.seismograms] may have already
    been pre-processed (i.e. already filtered) the default value for this
    parameter is [`False`][].
    """

    bandpass_fmin: float = field(
        default=ICCS_DEFAULTS.bandpass_fmin, validator=_clear_cache_on_update
    )
    """Bandpass filter minimum frequency (Hz). Only used if [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is `True`."""

    bandpass_fmax: float = field(
        default=ICCS_DEFAULTS.bandpass_fmax, validator=_clear_cache_on_update
    )
    """Bandpass filter maximum frequency (Hz). Only used if [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is `True`."""

    min_ccnorm: np.floating | float = ICCS_DEFAULTS.min_ccnorm
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
    _cc_seismograms: list[_EphemeralSeismogram] | None = field(init=False)
    _context_seismograms: list[_EphemeralSeismogram] | None = field(init=False)
    _ccnorms: np.ndarray | None = field(init=False)
    _cc_stack: MiniSeismogram | None = field(init=False)
    _context_stack: MiniSeismogram | None = field(init=False)
    _valid_pick_range: tuple[timedelta, timedelta] | None = field(init=False)
    _valid_time_window_range: tuple[timedelta, timedelta] | None = field(init=False)

    def __attrs_post_init__(self) -> None:
        self._clear_caches()

    def _clear_caches(self) -> None:
        """Clear all cached attributes."""
        self._cc_seismograms = None
        self._context_seismograms = None
        self._ccnorms = None
        self._cc_stack = None
        self._context_stack = None
        self._valid_pick_range = None
        self._valid_time_window_range = None

    def _prepare_seismograms(
        self,
        add_context: bool = False,
    ) -> list[_EphemeralSeismogram]:
        """Prepare cc_seismograms or context_seismograms."""

        return_seismograms: list[_EphemeralSeismogram] = []

        min_delta = min((s.delta for s in self.seismograms))

        for seismogram in self.seismograms:
            pick = seismogram.t1 or seismogram.t0
            window_start = pick + self.window_pre
            window_end = pick + self.window_post

            prepared_seismogram = _EphemeralSeismogram(parent_seismogram=seismogram)

            if self.bandpass_apply:
                bandpass(
                    prepared_seismogram,
                    self.bandpass_fmin,
                    self.bandpass_fmax,
                    zerophase=True,
                )

            if not np.isclose(
                to_seconds(prepared_seismogram.delta), to_seconds(min_delta)
            ):
                resample(prepared_seismogram, min_delta)

            if add_context:
                context_window_start = window_start - self.context_width
                context_window_end = window_end + self.context_width

                if (
                    context_window_start < seismogram.begin_time
                    or context_window_end > seismogram.end_time
                ):
                    pad(
                        prepared_seismogram,
                        context_window_start,
                        context_window_end,
                        mode="linear_ramp",
                        end_values=(0, 0),
                    )

                crop(prepared_seismogram, context_window_start, context_window_end)
                detrend(prepared_seismogram)
                normalize(prepared_seismogram, window_start, window_end)
            else:
                window(prepared_seismogram, window_start, window_end, self.ramp_width)
                normalize(prepared_seismogram)

            if seismogram.flip:
                prepared_seismogram.data *= -1

            return_seismograms.append(prepared_seismogram)

        # If all seismograms have the same length, return them now.
        if len(lengths := set(len(s) for s in return_seismograms)) == 1:
            return return_seismograms

        # Shorten seismograms if necessary and return.
        for s in return_seismograms:
            s.data = s.data[: min(lengths)]
        return return_seismograms

    @property
    def cc_seismograms(self) -> list[_EphemeralSeismogram]:
        """Returns the seismograms as used for the cross-correlation.

        These seismograms are derived from the input seismograms and used for
        the cross-correlation steps. Starting with the input seismograms, they
        are processed as follows:

        1. Bandpass filtered if
           [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is
           [`True`][].
        2. Resampled to the minimum sampling interval of all input seismograms
           (only if it is not equal in all seismograms).
        3. Cropped to `ramp_width` +  current time window + `ramp_width`.
        4. Detrended.
        5. Tapered using [`ramp_width`][pysmo.tools.iccs.ICCS.ramp_width]
           (tapered sections are *outside* time window).
        6. Normalised based on the highest absolute value within the cropped
           window. This step is done slightly differently in
           [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms]
           --see the documentation of that property for details.
        """

        if self._cc_seismograms is None:
            self._cc_seismograms = self._prepare_seismograms(add_context=False)
        return self._cc_seismograms

    @property
    def context_seismograms(self) -> list[_EphemeralSeismogram]:
        """Returns the seismograms with extra context for plotting.

        These seismograms are derived from the input seismograms and used
        primarily for plotting with extra context (e.g. when selecting new
        time window boundaries). Starting with the input seismograms, they are
        processed as follows:

        1. Bandpass filtered if
           [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is
           [`True`][].
        2. Resampled to the minimum sampling interval of all input seismograms
           (only if it is not equal in all seismograms).
        3. Cropped and/or padded to `context_width` +  current time window +
           `context_width`.
        4. Detrended.
        5. Normalised based on the highest absolute value within the selected
           time window (i.e. without the context).
        """

        if self._context_seismograms is None:
            self._context_seismograms = self._prepare_seismograms(add_context=True)
        return self._context_seismograms

    @property
    def ccnorms(self) -> np.ndarray:
        """Returns an array of the normalised cross-correlation coefficients."""

        if self._ccnorms is None:
            matrix = np.array([s.data for s in self.cc_seismograms])
            self._ccnorms = pearson_matrix_vector(matrix, self.stack.data)
        return self._ccnorms

    @property
    def stack(self) -> MiniSeismogram:
        """Returns the stacked [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]).

        The stack is calculated as the average of all seismograms with the
        attribute [`select`][pysmo.tools.iccs.ICCSSeismogram.select] set to
        [`True`][True]. The [`begin_time`][pysmo.MiniSeismogram.begin_time] of
        the returned stack is the average of the [`begin_time`]
        [pysmo.tools.iccs.ICCSSeismogram.begin_time] of the input seismograms.

        Returns:
            Stacked input seismograms.
        """
        if self._cc_stack is None:
            self._cc_stack = _create_stack(self.cc_seismograms)
        return self._cc_stack

    @property
    def context_stack(self) -> MiniSeismogram:
        """Returns the stacked [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms].

        Returns:
            Stacked input seismograms with context padding.
        """
        if self._context_stack is None:
            self._context_stack = _create_stack(self.context_seismograms)
        return self._context_stack

    def validate_pick(self, pick: np.timedelta64) -> bool:
        """Check if a new pick is valid.

        This checks if a new manual pick is valid for all selected seismograms.

        Args:
            pick: New pick to validate as numpy timedelta64.

        Returns:
            Whether the new pick is valid.
        """

        # first calculate valid pick range if not done yet
        if self._valid_pick_range is None:
            self._valid_pick_range = _calc_valid_pick_range(self)

        return self._valid_pick_range[0] <= pick <= self._valid_pick_range[1]

    def validate_time_window(
        self, window_pre: np.timedelta64, window_post: np.timedelta64
    ) -> bool:
        """Check if a new time window (relative to pick) is valid.

        Args:
            window_pre: New window start time to validate as numpy timedelta64.
            window_post: New window end time to validate as numpy timedelta64.

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

        return (
            self._valid_time_window_range[0] <= window_pre
            and window_post <= self._valid_time_window_range[1]
        )

    def __call__(
        self,
        autoflip: bool = False,
        autoselect: bool = False,
        convergence_limit: float = ICCS_DEFAULTS.convergence_limit,
        convergence_method: ConvergenceMethod = ICCS_DEFAULTS.convergence_method,
        max_iter: int = ICCS_DEFAULTS.max_iter,
        max_shift: np.timedelta64 | None = None,
    ) -> np.ndarray:
        """Run the iccs algorithm.

        Args:
            autoflip: Automatically toggle [`flip`][pysmo.tools.iccs.ICCSSeismogram.flip] attribute of seismograms.
            autoselect: Automatically set `select` attribute to `False` for poor quality seismograms.
            convergence_limit: Convergence limit at which the algorithm stops.
            convergence_method: Method to calculate convergence criterion.
            max_iter: Maximum number of iterations.
            max_shift: Maximum shift in seconds (see [`delay()`][pysmo.tools.signal.delay]).

        Returns:
            convergence: Array of convergence criterion values.
        """
        convergence_list = []

        for _ in range(max_iter):
            # Save the previous stack to calculate convergence criterion after updating the seismograms.
            prev_stack = clone_to_mini(MiniSeismogram, self.stack)

            # Get delays and correlation coefficients for all seismograms in one go
            delays, ccnorms = multi_delay(
                self.stack, self.cc_seismograms, abs_max=autoflip
            )

            # Update seismograms based on results and settings.
            for delay, ccnorm, cc_seismogram in zip(
                delays, ccnorms, self.cc_seismograms
            ):
                _update_seismogram(
                    delay,
                    ccnorm,
                    cc_seismogram.parent_seismogram,
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


def _update_seismogram(
    delay: np.timedelta64,
    ccnorm: float,
    seismogram: ICCSSeismogram,
    autoflip: bool,
    autoselect: bool,
    min_ccnorm_for_autoselect: np.floating | float,
    current_window: tuple[np.timedelta64, np.timedelta64],
) -> None:
    """Update ICCSSeismogram attributes based on cross-correlation results.

    Optionally toggles ``flip`` (if ``autoflip`` is True and the correlation
    coefficient is negative) and ``select`` (if ``autoselect`` is True and
    the absolute correlation coefficient is below the threshold). The pick
    ``t1`` is updated unless the new value would fall outside the seismogram
    limits.

    Args:
        delay: Time shift from cross-correlation as numpy timedelta64.
        ccnorm: Normalised cross-correlation coefficient.
        seismogram: Seismogram to update.
        autoflip: Automatically toggle the ``flip`` attribute.
        autoselect: Automatically toggle the ``select`` attribute.
        min_ccnorm_for_autoselect: Threshold for ``autoselect``.
        current_window: Current ``(window_pre, window_post)`` tuple as numpy timedelta64.
    """

    if autoflip and ccnorm < 0:
        seismogram.flip = not seismogram.flip
        ccnorm = abs(ccnorm)

    if autoselect:
        seismogram.select = bool(ccnorm >= min_ccnorm_for_autoselect)

    updated_t1 = (seismogram.t1 or seismogram.t0) + delay
    limit_pre = seismogram.begin_time - current_window[0]
    limit_post = seismogram.end_time - current_window[1]

    if not limit_pre <= updated_t1 <= limit_post:
        warnings.warn(
            f"Refusing to update t1 for {seismogram=}. Would move out of limits - consider reducing window size."
        )
        return

    seismogram.t1 = updated_t1


def _create_stack(seismograms: Sequence[_EphemeralSeismogram]) -> MiniSeismogram:
    """Create a stack by averaging all selected seismograms.

    Args:
        seismograms: Prepared seismograms to stack.

    Returns:
        A new seismogram whose data is the mean of all selected input seismograms.
    """
    begin_time = average_datetimes(
        [p.begin_time for p in seismograms if p.parent_seismogram.select]
    )
    delta = seismograms[0].delta
    data = np.mean(
        np.array([p.data for p in seismograms if p.parent_seismogram.select]),
        axis=0,
    )
    return MiniSeismogram(begin_time=begin_time, delta=delta, data=data)


def _calc_convergence(
    current_stack: Seismogram,
    prev_stack: Seismogram,
    method: ConvergenceMethod,
) -> float:
    """Calculate criterion of convergence.

    This function calculates a criterion of convergence based on the current and
    previous stack using one of the following methods:

    - Convergence by correlation coefficient.
    - Convergence by change of stack

    Args:
        current_stack: Current stack.
        prev_stack: Stack from last iteration.
        method: Method of convergence criterion calculation.
    """
    if method == ConvergenceMethod.corrcoef:
        covr, _ = pearsonr(current_stack.data, prev_stack.data)
        return 1 - float(covr)
    elif method == ConvergenceMethod.change:
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
