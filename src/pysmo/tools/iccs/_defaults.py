from ._types import ConvergenceMethod
from dataclasses import dataclass, field
from matplotlib.colors import Colormap
import matplotlib as mpl
import numpy as np


@dataclass(frozen=True)
class _IccsDefaults:
    """Defaults used in ICCS."""

    # ------------------------------------------------------------------------
    # ICCS attribute defaults
    # ------------------------------------------------------------------------
    window_pre: np.timedelta64 = np.timedelta64(-15_000_000, "us")  # -15 seconds
    window_post: np.timedelta64 = np.timedelta64(15_000_000, "us")  # 15 seconds
    context_width: np.timedelta64 = np.timedelta64(20_000_000, "us")  # 20 seconds
    ramp_width: np.timedelta64 | float = 0.1
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
