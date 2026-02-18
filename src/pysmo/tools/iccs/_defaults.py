from ._types import ConvergenceMethod
from dataclasses import dataclass, field
from matplotlib.colors import Colormap
from pandas import Timedelta
import matplotlib as mpl
import numpy as np


@dataclass(frozen=True)
class _IccsDefaults:
    """Defaults used in ICCS."""

    # ------------------------------------------------------------------------
    # ICCS attribute defaults
    # ------------------------------------------------------------------------
    window_pre: Timedelta = Timedelta(seconds=-15)
    window_post: Timedelta = Timedelta(seconds=15)
    context_width: Timedelta = Timedelta(seconds=20)
    ramp_width: Timedelta | float = 0.1
    min_ccnorm: np.floating | float = 0.5
    bandpass_apply: bool = False
    bandpass_fmin: float = 0.05
    bandpass_fmax: float = 2

    # ------------------------------------------------------------------------
    # ICCS __call__ defaults
    # ------------------------------------------------------------------------
    convergence_limit: float = 1e-5
    convergence_method: ConvergenceMethod = ConvergenceMethod.corrcoef
    max_iter: int = 10

    # ------------------------------------------------------------------------
    # function defaults
    # ------------------------------------------------------------------------
    img_cmap: Colormap = field(default_factory=lambda: mpl.colormaps["RdBu"])
    stack_cmap: Colormap = field(default_factory=lambda: mpl.colormaps["cool"])


ICCS_DEFAULTS = _IccsDefaults()
