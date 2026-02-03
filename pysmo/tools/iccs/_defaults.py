from dataclasses import dataclass, field
from matplotlib.colors import Colormap
from datetime import timedelta
from typing import TYPE_CHECKING
import matplotlib as mpl
import numpy as np

if TYPE_CHECKING:
    from ._iccs import CONVERGENCE_METHOD


@dataclass(frozen=True)
class _IccsDefaults:
    """Defaults used in ICCS."""

    # ------------------------------------------------------------------------
    # ICCS attribute defaults
    # ------------------------------------------------------------------------

    WINDOW_PRE: timedelta = timedelta(seconds=-15)
    WINDOW_POST: timedelta = timedelta(seconds=15)
    PLOT_PADDING: timedelta = timedelta(seconds=20)
    RAMP_WIDTH: timedelta | float = 0.0
    MIN_CCNORM: np.floating | float = 0.5

    # ------------------------------------------------------------------------
    # ICCS __call__ defaults
    # ------------------------------------------------------------------------

    CONVERGENCE_LIMIT: float = 10e-6
    CONVERGENCE_METHOD: "CONVERGENCE_METHOD" = "corrcoef"
    MAX_ITER: int = 10

    # ------------------------------------------------------------------------
    # function defaults
    # ------------------------------------------------------------------------

    IMG_CMAP: Colormap = field(default_factory=lambda: mpl.colormaps["RdBu"])
    STACK_CMAP: Colormap = field(default_factory=lambda: mpl.colormaps["cool"])


ICCS_DEFAULTS = _IccsDefaults()
