"""The ICCS class and functions used within the class."""

import warnings
from collections.abc import Sequence

import numpy as np
import pandas as pd
from attrs import Attribute, define, field, setters, validate, validators
from numpy.linalg import norm
from scipy.stats.mstats import pearsonr

from pysmo import MiniSeismogram, Seismogram
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.functions import (
    clone_to_mini,
    crop,
    detrend,
    normalize,
    pad,
    resample,
    window,
)
from pysmo.lib.validators import convert_to_timedelta
from pysmo.tools.signal import bandpass, mccc, multi_delay
from pysmo.tools.utils import average_datetimes, pearson_matrix_vector
from pysmo.typing import (
    NegativeTimedelta,
    NonNegativeNumber,
    NonNegativeTimedelta,
    PositiveTimedelta,
)

from ._defaults import IccsDefaults
from ._types import ConvergenceMethod, IccsResult, IccsSeismogram, McccResult

__all__ = ["ICCS"]


def _compute_ramp(
    ramp_width: float | pd.Timedelta,
    window_pre: pd.Timedelta,
    window_post: pd.Timedelta,
) -> pd.Timedelta:
    """Compute the taper ramp duration, matching `pysmo.functions.window` semantics.

    Args:
        ramp_width: Ramp width, either as an absolute `pandas.Timedelta`
            or as a non-negative float fraction of the window duration.
        window_pre: Start of the window relative to the pick (negative).
        window_post: End of the window relative to the pick (positive).

    Returns:
        Absolute ramp duration as a `pandas.Timedelta`.
    """
    if isinstance(ramp_width, pd.Timedelta):
        return ramp_width
    return ramp_width * (window_post - window_pre)


def _on_setattr_clear_cache[T](instance: "ICCS", attribute: Attribute, value: T) -> T:
    """Setter that causes cached attributes to be cleared when their value changes."""

    if (current := getattr(instance, attribute.name)) is value:
        return value

    if isinstance(current, np.ndarray) and isinstance(value, np.ndarray):
        if np.array_equal(current, value):
            return value

    elif (current == value) is True:
        return value

    instance.clear_cache()

    if attribute.name == "seismograms":
        object.__setattr__(instance, "seismograms", value)
        validate(instance)

    return value


def _validate_window_pre(
    instance: "ICCS", attribute: Attribute, value: pd.Timedelta
) -> None:
    """Ensure window_pre fits within all seismograms, accounting for the taper ramp."""
    ramp = _compute_ramp(instance.ramp_width, value, instance.window_post)
    if not (value >= instance._max_td_pre + ramp):
        raise ValueError("window_pre is too low for one or more seismograms.")


def _validate_window_post(
    instance: "ICCS", attribute: Attribute, value: pd.Timedelta
) -> None:
    """Ensure window_post fits within all seismograms, accounting for the taper ramp."""
    ramp = _compute_ramp(instance.ramp_width, instance.window_pre, value)
    if not (value <= instance._min_td_post - ramp):
        raise ValueError("window_post is too high for one or more seismograms.")


def _validate_ramp_width(
    instance: "ICCS",
    attribute: Attribute,
    value: NonNegativeTimedelta | NonNegativeNumber,
) -> None:
    ramp = _compute_ramp(value, instance.window_pre, instance.window_post)
    if ramp < pd.Timedelta(0):
        raise ValueError("ramp_width must be non-negative.")
    if not (
        ramp <= instance.window_pre - instance._max_td_pre
        and ramp <= instance._min_td_post - instance.window_post
    ):
        raise ValueError("ramp_width is too high for one or more seismograms.")


@define(slots=True)
class _EphemeralSeismogram(SeismogramEndtimeMixin):
    """A Seismogram class used internally in ICCS to store the prepared seismograms.

    This class is not intended for use outside of the ICCS class, and is not
    exposed in the public API. It is used to store the prepared seismograms
    (i.e. the seismograms that are cropped, tapered, and normalised based on
    the current pick and time window) for use in the cross-correlation and
    stacking. The data in these seismograms are modified on the fly when the
    picks and time windows are updated, but they are not intended to be modified
    directly by users.
    """

    parent_seismogram: IccsSeismogram
    """Reference to the parent IccsSeismogram from which this ephemeral seismogram is derived."""

    begin_time: pd.Timestamp = field(init=False)
    """Seismogram begin time."""

    delta: pd.Timedelta = field(init=False)
    """Seismogram sampling interval."""

    data: np.ndarray = field(init=False)
    """Seismogram data."""

    def __attrs_post_init__(self) -> None:
        self.begin_time = self.parent_seismogram.begin_time
        self.delta = self.parent_seismogram.delta
        self.data = self.parent_seismogram.data.copy()


@define(slots=True)
class ICCS:
    """Class to store a list of [`IccsSeismograms`][pysmo.tools.iccs.IccsSeismogram] and run the ICCS algorithm.

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
        [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram] class for use
        with the [`ICCS`][pysmo.tools.iccs.ICCS] class:

        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo.tools.iccs import MiniIccsSeismogram
        >>> from pathlib import Path
        >>>
        >>> sacfiles = sorted(Path("iccs-example/").glob("*.bhz"))
        >>>
        >>> seismograms = []
        >>> for sacfile in sacfiles:
        ...     sac = SAC.from_file(sacfile)
        ...     update = {"t0": sac.timestamps.t0}
        ...     iccs_seismogram = clone_to_mini(MiniIccsSeismogram, sac.seismogram, update=update)
        ...     seismograms.append(iccs_seismogram)
        ...
        >>>
        ```

        To better illustrate the different modes of running the ICCS algorithm,
        we modify the data and picks in the seismograms to make them **worse**
        than they actually are:

        ```python
        >>> import pandas as pd
        >>> from copy import deepcopy
        >>> import numpy as np
        >>>
        >>> # change the sign of the data in the first seismogram
        >>> seismograms[0].data *= -1
        >>>
        >>> # move the initial pick 2 seconds earlier in second seismogram
        >>> seismograms[1].t0 += pd.Timedelta(seconds=-2)
        >>>
        >>> # move the initial pick 2 seconds later in third seismogram
        >>> seismograms[2].t0 += pd.Timedelta(seconds=2)
        >>>
        >>> # create a seismogram with completely random data
        >>> iccs_random: MiniIccsSeismogram = deepcopy(seismograms[-1])
        >>> np.random.seed(42)  # set this for consistent results during testing
        >>> iccs_random.data = np.random.rand(len(iccs_random.data))
        >>> seismograms.append(iccs_random)
        >>>
        ```

        We can now create an instance of the [`ICCS`][pysmo.tools.iccs.ICCS]
        class and plot the initial [`stack`][pysmo.tools.iccs.ICCS.stack] and
        [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]:

        ```python
        >>> from pysmo.tools.iccs import ICCS, plot_stack
        >>> iccs = ICCS(seismograms)
        >>> fig, ax = plot_stack(iccs, context=False)
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
        >>> fig, ax = plot_stack(iccs, context=False)
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
        >>> fig, ax = plot_stack(iccs, context=False)
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
        >>> fig, ax = plot_stack(iccs, context=False)
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

    seismograms: Sequence[IccsSeismogram] = field(
        factory=list[IccsSeismogram], on_setattr=_on_setattr_clear_cache
    )
    """Input seismograms.

    These are the source seismograms from which the
    [ephemeral seismograms][pysmo.tools.iccs#ephemeral-seismograms]
    (cross-correlation and context seismograms) are derived on demand.
    The ephemeral seismograms are cached and regenerated automatically
    whenever a controlling attribute such as
    [`window_pre`][pysmo.tools.iccs.ICCS.window_pre] or
    [`window_post`][pysmo.tools.iccs.ICCS.window_post] changes.

    Warning:
        Assigning a new list to this attribute clears the cache automatically.
        *Mutating* the list in place (e.g. with `append`, `remove`, or direct
        index assignment) bypasses the setter and does **not** clear the cache.
        Call [`clear_cache`][pysmo.tools.iccs.ICCS.clear_cache] manually after
        any such in-place mutation.

    Tip:
        When a seismogram is of sufficiently poor quality that it should play no
        further role in the analysis, consider *removing* it from this list rather
        than simply setting its
        [`select`][pysmo.tools.iccs.IccsSeismogram.select] attribute to
        `False`. A deselected seismogram is excluded from the stack and
        correlation output, but its pick and data span still constrain the valid
        ranges for [`window_pre`][pysmo.tools.iccs.ICCS.window_pre],
        [`window_post`][pysmo.tools.iccs.ICCS.window_post], and pick updates —
        because all seismograms (selected or not) are used to generate the
        ephemeral seismograms. A badly drifting pick on a deselected seismogram
        can therefore make it impossible to set useful window or pick ranges for
        the remaining good seismograms.
    """

    window_pre: NegativeTimedelta = field(
        default=IccsDefaults.window_pre,
        validator=[validators.lt(pd.Timedelta(0)), _validate_window_pre],
        on_setattr=setters.pipe(setters.validate, _on_setattr_clear_cache),
    )
    """Beginning of the time window relative to the pick."""

    window_post: PositiveTimedelta = field(
        default=IccsDefaults.window_post,
        validator=[validators.gt(pd.Timedelta(0)), _validate_window_post],
        on_setattr=setters.pipe(setters.validate, _on_setattr_clear_cache),
    )
    """End of the time window relative to the pick."""

    ramp_width: NonNegativeTimedelta | NonNegativeNumber = field(
        default=IccsDefaults.ramp_width,
        validator=_validate_ramp_width,
        on_setattr=setters.pipe(setters.validate, _on_setattr_clear_cache),
    )
    """Width of taper ramp up and down.

    Warning:
        Can be either a timedelta or a float, but they mean slightly different
        things. A float is interpreted as a fraction of the window duration,
        while a timedelta is an absolute duration. See the documentation of
        of [`pysmo.functions.window()`][pysmo.functions.window] for details.
    """

    context_width: PositiveTimedelta = field(
        default=IccsDefaults.context_width,
        converter=convert_to_timedelta,
        validator=validators.gt(pd.Timedelta(0)),
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Context padding to apply before and after the time window.

    This padding is *not* used for the cross-correlation."""

    bandpass_apply: bool = field(
        default=IccsDefaults.bandpass_apply,
        converter=bool,
        validator=validators.instance_of(bool),
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
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
        default=IccsDefaults.bandpass_fmin,
        converter=float,
        validator=validators.instance_of(float),
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Bandpass filter minimum frequency (Hz). Only used if [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is `True`."""

    bandpass_fmax: float = field(
        default=IccsDefaults.bandpass_fmax,
        converter=float,
        validator=validators.instance_of(float),
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Bandpass filter maximum frequency (Hz). Only used if [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] is `True`."""

    min_ccnorm: float = field(
        default=IccsDefaults.min_ccnorm,
        converter=float,
        validator=validators.instance_of(float),
        on_setattr=setters.pipe(
            setters.convert, setters.validate, _on_setattr_clear_cache
        ),
    )
    """Minimum normalised cross-correlation coefficient for seismograms.

    When the ICCS algorithm is [executed][pysmo.tools.iccs.ICCS.__call__],
    the cross-correlation coefficient for each seismogram is calculated after
    each iteration. If `autoselect` is set to `True`, the
    [`select`][pysmo.tools.iccs.IccsSeismogram.select] attribute of seismograms
    with with correlation coefficients below this value is set to `False`, and
    they are no longer used for the [`stack`][pysmo.tools.iccs.ICCS.stack].
    """

    # The following attributes are cached to prevent unnecessary processing.
    # Setting the caches to None will force a new calculation when they are
    # requested.
    _cc_seismograms_cache: list[_EphemeralSeismogram] | None = field(
        default=None, init=False
    )
    """Cached list of the prepared seismograms for cross-correlation."""
    _context_seismograms_cache: list[_EphemeralSeismogram] | None = field(
        default=None, init=False
    )
    """Cached list of the prepared seismograms with context padding."""
    _ccnorms_cache: np.ndarray | None = field(default=None, init=False)
    """Cached array of the normalised cross-correlation coefficients."""
    _cc_stack_cache: MiniSeismogram | None = field(default=None, init=False)
    """Cached stack of the prepared seismograms for cross-correlation."""
    _context_stack_cache: MiniSeismogram | None = field(default=None, init=False)
    """Cached stack of the prepared seismograms with context padding."""
    _max_td_pre_cache: pd.Timedelta | None = field(default=None, init=False)
    """Cached maximum negative time delta between pick and seismogram begin_time."""
    _min_td_post_cache: pd.Timedelta | None = field(default=None, init=False)
    """Cached minimum positive time delta between pick and seismogram end_time."""
    _valid_pick_range_cache: tuple[pd.Timedelta, pd.Timedelta] | None = field(
        default=None, init=False
    )

    def clear_cache(self) -> None:
        """Clear all cached ephemeral seismograms, stacks, and derived results.

        Ephemeral seismograms (both cross-correlation and context variants),
        their stacks, cross-correlation norms, and the valid pick and window
        ranges are all computed on demand and cached to avoid redundant work.
        The cache is invalidated automatically when a controlling attribute
        such as [`window_pre`][pysmo.tools.iccs.ICCS.window_pre],
        [`window_post`][pysmo.tools.iccs.ICCS.window_post], or
        [`seismograms`][pysmo.tools.iccs.ICCS.seismograms] is *reassigned*.

        Call this method manually after any in-place mutation of
        [`seismograms`][pysmo.tools.iccs.ICCS.seismograms] (e.g. `append`,
        `remove`, or index assignment) to ensure all ephemeral seismograms and
        derived results are regenerated from the updated input.
        """
        self._cc_seismograms_cache = None
        self._context_seismograms_cache = None
        self._ccnorms_cache = None
        self._cc_stack_cache = None
        self._context_stack_cache = None
        self._max_td_pre_cache = None
        self._min_td_post_cache = None
        self._valid_pick_range_cache = None

    @property
    def _ramp_width_timedelta(self) -> pd.Timedelta:
        """Ramp width as a `pandas.Timedelta`, computed from the current window.

        For a float `ramp_width`, the duration is computed as a fraction of the
        window duration `(window_post - window_pre)`, consistent with the
        behaviour of `pysmo.functions.window`.
        """
        return _compute_ramp(self.ramp_width, self.window_pre, self.window_post)

    @property
    def _min_delta(self) -> pd.Timedelta:
        """Minimum sampling interval across all seismograms."""
        if not self.seismograms:
            return pd.Timedelta(0)
        return min(s.delta for s in self.seismograms)

    @property
    def _max_td_pre(self) -> pd.Timedelta:
        """Maximum negative time delta between pick and seismogram begin_time.

        This property is used to calculate valid values for updating picks and
        attributes. Specifically:

        - new_pick > old_pick + _max_td_pre - window_pre + ramp_width
        - window_pre >= _max_td_pre + ramp_width
        - ramp_width <= window_pre - _max_td_pre
        """
        if not self.seismograms:
            return pd.Timedelta(days=-365 * 100)

        if self._max_td_pre_cache is None:
            self._max_td_pre_cache = max(
                s.begin_time - (s.t0 if pd.isnull(s.t1) else s.t1)
                for s in self.seismograms
            )
        return self._max_td_pre_cache

    @property
    def _min_td_post(self) -> pd.Timedelta:
        """Minimum positive time delta between pick and seismogram end_time.

        This property is used to calculate valid values for updating picks and
        attributes. Specifically:

        - new_pick < old_pick + _min_td_post - window_post - ramp_width
        - window_post <= _min_td_post - ramp_width
        - ramp_width <= _min_td_post - window_post
        """
        if not self.seismograms:
            return pd.Timedelta(days=365 * 100)

        if self._min_td_post_cache is None:
            self._min_td_post_cache = min(
                s.end_time - (s.t0 if pd.isnull(s.t1) else s.t1)
                for s in self.seismograms
            )
        return self._min_td_post_cache

    @property
    def cc_seismograms(self) -> list[_EphemeralSeismogram]:
        """Return the seismograms as used for the cross-correlation.

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

        if self._cc_seismograms_cache is None:
            self._cc_seismograms_cache = _prepare_seismograms(self, add_context=False)
        return self._cc_seismograms_cache

    @property
    def selected_cc_seismograms(self) -> list[_EphemeralSeismogram]:
        """Return a list of cc_seismograms with select=True."""
        return [s for s in self.cc_seismograms if s.parent_seismogram.select]

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

        if self._context_seismograms_cache is None:
            self._context_seismograms_cache = _prepare_seismograms(
                self, add_context=True
            )
        return self._context_seismograms_cache

    @property
    def ccnorms(self) -> np.ndarray:
        """Returns an array of the normalised cross-correlation coefficients."""

        if self._ccnorms_cache is None:
            matrix = np.array([s.data for s in self.cc_seismograms])
            self._ccnorms_cache = pearson_matrix_vector(matrix, self.stack.data)
        return self._ccnorms_cache

    @property
    def stack(self) -> MiniSeismogram:
        """Returns the stacked [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]).

        The stack is calculated as the average of all seismograms with the
        attribute [`select`][pysmo.tools.iccs.IccsSeismogram.select] set to
        [`True`][True]. The [`begin_time`][pysmo.MiniSeismogram.begin_time] of
        the returned stack is the average of the [`begin_time`]
        [pysmo.tools.iccs.IccsSeismogram.begin_time] of the input seismograms.

        Returns:
            Stacked input seismograms.
        """
        if self._cc_stack_cache is None:
            self._cc_stack_cache = _create_stack(self.cc_seismograms)
        return self._cc_stack_cache

    @property
    def context_stack(self) -> MiniSeismogram:
        """Returns the stacked [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms].

        Returns:
            Stacked input seismograms with context padding.
        """
        if self._context_stack_cache is None:
            self._context_stack_cache = _create_stack(self.context_seismograms)
        return self._context_stack_cache

    def validate_pick(self, pick: pd.Timedelta) -> bool:
        """Check whether a new pick is valid given all seismograms in the instance.

        The valid pick range is computed from every seismogram in
        [`seismograms`][pysmo.tools.iccs.ICCS.seismograms], including those with
        [`select`][pysmo.tools.iccs.IccsSeismogram.select] set to
        [`False`][False]. A pick is considered valid if it lies within this
        global range; selection only affects stacking, not the validity bounds.

        Args:
            pick: New pick to validate.

        Returns:
            Whether the new pick is valid.
        """

        if self._valid_pick_range_cache is None:
            self._valid_pick_range_cache = _calc_valid_pick_range(self)

        return (
            self._valid_pick_range_cache[0] <= pick <= self._valid_pick_range_cache[1]
        )

    def validate_time_window(
        self, window_pre: pd.Timedelta, window_post: pd.Timedelta
    ) -> bool:
        """Check if a new time window (relative to pick) is valid.

        Validates that the proposed window fits within every seismogram,
        accounting for the taper ramp. The ramp duration is computed from
        the proposed `window_pre` and `window_post` values, consistent
        with how `pysmo.functions.window` computes it for float
        `ramp_width`.

        Args:
            window_pre: Proposed window start time (negative, relative to pick).
            window_post: Proposed window end time (positive, relative to pick).

        Returns:
            Whether the new time window is valid for all seismograms.
        """

        if window_pre >= window_post:
            return False

        if window_pre > -self._min_delta:
            return False

        if window_post < self._min_delta:
            return False

        ramp = _compute_ramp(self.ramp_width, window_pre, window_post)
        for s in self.seismograms:
            pick = s.t0 if pd.isnull(s.t1) else s.t1
            if window_pre < s.begin_time - pick + ramp:
                return False
            if window_post > s.end_time - pick - ramp:
                return False
        return True

    def __call__(
        self,
        autoflip: bool = False,
        autoselect: bool = False,
        convergence_limit: float = IccsDefaults.convergence_limit,
        convergence_method: ConvergenceMethod = IccsDefaults.convergence_method,
        max_iter: int = IccsDefaults.max_iter,
        max_shift: pd.Timedelta | None = None,
    ) -> IccsResult:
        """Run the iccs algorithm.

        Args:
            autoflip: Automatically toggle [`flip`][pysmo.tools.iccs.IccsSeismogram.flip] attribute of seismograms.
            autoselect: Automatically set `select` attribute to `False` for poor quality seismograms.
            convergence_limit: Convergence limit at which the algorithm stops.
            convergence_method: Method to calculate convergence criterion.
            max_iter: Maximum number of iterations.
            max_shift: Maximum shift in seconds (see [`delay()`][pysmo.tools.signal.delay]).

        Returns:
            An [`IccsResult`][pysmo.tools.iccs.IccsResult] containing the
            convergence history and whether the convergence limit was reached.
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

            self.clear_cache()

            convergence = _calc_convergence(self.stack, prev_stack, convergence_method)
            convergence_list.append(convergence)
            if convergence <= convergence_limit:
                break

        converged = bool(convergence_list and convergence_list[-1] <= convergence_limit)
        return IccsResult(convergence=np.array(convergence_list), converged=converged)

    def run_mccc(
        self,
        all_seismograms: bool = False,
        min_cc: float = IccsDefaults.mccc_min_cc,
        damping: float = IccsDefaults.mccc_damp,
    ) -> McccResult:
        """Refine picks with the MCCC algorithm.

        This updates the picks of the seismograms with
        [`mccc`][pysmo.tools.signal.mccc]. It can be executed at any point to
        update picks. However, it will not autoselect or autoflip seismograms.
        It is therefore recommended as final step to refine the results of
        [`ICCS()`][pysmo.tools.iccs.ICCS.__call__].

        Args:
            all_seismograms: Whether to run MCCC on all seismograms or only on
                those with `select` set to `True`. Default is `False` (only on
                selected seismograms).
            min_cc: Minimum correlation coefficient required to include a pair
                in the inversion.
            damping: Tikhonov regularization strength. Set to 0 to disable.

        Returns:
            A [`McccResult`][pysmo.tools.iccs.McccResult] containing the
            updated picks and MCCC diagnostic values.
        """
        seismograms = (
            self.cc_seismograms if all_seismograms else self.selected_cc_seismograms
        )

        delays, errors, rmse, cc_means, cc_errs = mccc(
            seismograms, min_cc=min_cc, damping=damping
        )

        picks: list[pd.Timestamp] = []

        for delay, cc_seis in zip(delays, seismograms):
            seis = cc_seis.parent_seismogram
            _update_seismogram(
                delay,
                ccnorm=None,
                seismogram=seis,
                autoflip=False,
                autoselect=False,
                min_ccnorm_for_autoselect=self.min_ccnorm,
                current_window=(self.window_pre, self.window_post),
            )
            # After update (or attempted update), retrieve the pick.
            # Fallback to t0 if t1 is None (e.g. if update failed and was None).
            picks.append(seis.t0 if pd.isnull(seis.t1) else seis.t1)

        self.clear_cache()
        return McccResult(
            picks=picks, errors=errors, rmse=rmse, cc_means=cc_means, cc_errs=cc_errs
        )

    def update_all_picks(self, pickdelta: pd.Timedelta) -> None:
        """Update [`t1`][pysmo.tools.iccs.IccsSeismogram.t1] in all seismograms by the same amount.

        Args:
            pickdelta: delta applied to all picks.

        Raises:
            ValueError: If the new t1 is outside the valid range.
        """

        if not self.validate_pick(pickdelta):
            raise ValueError(
                "New t1 is outside the valid range. Consider reducing the time window."
            )

        for seismogram in self.seismograms:
            current_pick = seismogram.t0 if pd.isnull(seismogram.t1) else seismogram.t1
            seismogram.t1 = current_pick + pickdelta
        self.clear_cache()  # seismograms and stack need to be refreshed


def _update_seismogram(
    delay: pd.Timedelta,
    ccnorm: float | None,
    seismogram: IccsSeismogram,
    autoflip: bool,
    autoselect: bool,
    min_ccnorm_for_autoselect: np.floating | float,
    current_window: tuple[pd.Timedelta, pd.Timedelta],
) -> None:
    """Update IccsSeismogram attributes based on cross-correlation results.

    Optionally toggles `flip` (if `autoflip` is True and the correlation
    coefficient is negative) and `select` (if `autoselect` is True and
    the absolute correlation coefficient is below the threshold). The pick
    `t1` is updated unless the new value would fall outside the seismogram
    limits.

    Args:
        delay: Time shift from cross-correlation.
        ccnorm: Normalised cross-correlation coefficient. If it is `None`,
            no changes to `flip` and `select` will be made.
        seismogram: Seismogram to update.
        autoflip: Automatically toggle the `flip` attribute.
        autoselect: Automatically toggle the `select` attribute.
        min_ccnorm_for_autoselect: Threshold for `autoselect`.
        current_window: Current `(window_pre, window_post)` tuple.
    """
    if ccnorm is not None:
        if autoflip and ccnorm < 0:
            seismogram.flip = not seismogram.flip
            ccnorm = abs(ccnorm)

        if autoselect:
            seismogram.select = bool(ccnorm >= min_ccnorm_for_autoselect)

    updated_t1 = (seismogram.t0 if pd.isnull(seismogram.t1) else seismogram.t1) + delay
    limit_pre = seismogram.begin_time - current_window[0]
    limit_post = seismogram.end_time - current_window[1]

    if not limit_pre <= updated_t1 <= limit_post:
        warnings.warn(
            f"Refusing to update t1 for {seismogram=}. Would move out of limits - consider reducing window size."
        )
        return

    seismogram.t1 = updated_t1


def _prepare_seismograms(
    instance: ICCS, add_context: bool = False
) -> list[_EphemeralSeismogram]:
    """Prepare cc_seismograms or context_seismograms."""

    if not instance.seismograms:
        return []

    ephemeral_seismograms: list[_EphemeralSeismogram] = []

    min_delta = instance._min_delta

    for seismogram in instance.seismograms:
        pick = seismogram.t0 if pd.isnull(seismogram.t1) else seismogram.t1
        window_start = pick + instance.window_pre
        window_end = pick + instance.window_post

        ephemeral_seismogram = _EphemeralSeismogram(parent_seismogram=seismogram)

        if instance.bandpass_apply:
            bandpass(
                ephemeral_seismogram,
                instance.bandpass_fmin,
                instance.bandpass_fmax,
                zerophase=True,
            )

        if not np.isclose(
            ephemeral_seismogram.delta.total_seconds(), min_delta.total_seconds()
        ):
            resample(ephemeral_seismogram, min_delta)

        if add_context:
            context_window_start = window_start - instance.context_width
            context_window_end = window_end + instance.context_width

            if (
                context_window_start < seismogram.begin_time
                or context_window_end > seismogram.end_time
            ):
                pad(
                    ephemeral_seismogram,
                    context_window_start,
                    context_window_end,
                    mode="linear_ramp",
                    end_values=(0, 0),
                )

            crop(ephemeral_seismogram, context_window_start, context_window_end)
            detrend(ephemeral_seismogram)
            normalize(ephemeral_seismogram, window_start, window_end)
        else:
            window(ephemeral_seismogram, window_start, window_end, instance.ramp_width)
            normalize(ephemeral_seismogram)

        if seismogram.flip:
            ephemeral_seismogram.data *= -1

        ephemeral_seismograms.append(ephemeral_seismogram)

    # If all seismograms have the same length, return them now.
    if len(lengths := set(len(s.data) for s in ephemeral_seismograms)) == 1:
        return ephemeral_seismograms

    # Shorten seismograms if necessary and return (floating-point precision
    # can cause small differences in length after resampling). We cut off
    # at the end so the `begin_time` will not change.
    for s in ephemeral_seismograms:
        s.data = s.data[: min(lengths)]
    return ephemeral_seismograms


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
            / len(current_stack.data)
        )
    raise ValueError(f"Unknown convergence method: {method}.")


def _calc_valid_pick_range(instance: ICCS) -> tuple[pd.Timedelta, pd.Timedelta]:
    """Calculate the valid shift range for updating the pick.

    The pick delta must ensure there is enough space on either end of every
    seismogram (selected or not) to accommodate the time window and ramp,
    because `_prepare_seismograms` processes all seismograms.

    Args:
        instance: The `ICCS` instance to compute the valid range for.

    Returns:
        A `(min_pick_delta, max_pick_delta)` tuple of valid shift bounds.
    """
    if not instance.seismograms:
        return pd.Timedelta(days=-365 * 100), pd.Timedelta(days=365 * 100)

    td_pre_values = []
    td_post_values = []
    for s in instance.seismograms:
        pick = s.t0 if pd.isnull(s.t1) else s.t1
        td_pre_values.append(s.begin_time - pick - instance.window_pre)
        td_post_values.append(s.end_time - pick - instance.window_post)

    ramp = instance._ramp_width_timedelta
    return max(td_pre_values) + ramp, min(td_post_values) - ramp
