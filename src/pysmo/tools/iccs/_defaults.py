from ._types import CONVERGENCE_METHOD
from dataclasses import dataclass, field
from matplotlib.colors import Colormap
from datetime import timedelta
import matplotlib as mpl
import numpy as np


@dataclass(frozen=True)
class _IccsDefaults:
    """Defaults used in ICCS."""

    # ------------------------------------------------------------------------
    # ICCS attribute defaults
    # ------------------------------------------------------------------------
    window_pre: timedelta = timedelta(seconds=-15)
    window_post: timedelta = timedelta(seconds=15)
    context_width: timedelta = timedelta(seconds=20)
    ramp_width: timedelta | float = 0.1
    min_ccnorm: np.floating | float = 0.5

    # ------------------------------------------------------------------------
    # ICCS __call__ defaults
    # ------------------------------------------------------------------------
    convergence_limit: float = 1e-5
    convergence_method: CONVERGENCE_METHOD = CONVERGENCE_METHOD.corrcoef
    max_iter: int = 10

    # ------------------------------------------------------------------------
    # function defaults
    # ------------------------------------------------------------------------
    img_cmap: Colormap = field(default_factory=lambda: mpl.colormaps["RdBu"])
    stack_cmap: Colormap = field(default_factory=lambda: mpl.colormaps["cool"])


ICCS_DEFAULTS = _IccsDefaults()
