"""Extra plotting functions for the ICCS module.

Most of this module's contents are internal helpers for the higher-level
plotting functions (e.g. `plot_stack`, `update_pick`) exposed from the
`pysmo.tools.iccs` namespace, and are not meant to be used directly. The
exceptions are `draw_common_stack` and `draw_common_matrix_image`, lower-level
drawing primitives exposed for users who wish to customise their own plotting
workflows.
"""

from ...._utils import export_module_names
from ._bandpass import update_bandpass
from ._matrix_image import draw_common_matrix_image, plot_matrix_image
from ._min_cc import update_min_cc
from ._pick import update_pick
from ._stack import draw_common_stack, plot_stack
from ._timewindow import update_timewindow

__all__ = [
    "draw_common_matrix_image",
    "draw_common_stack",
    "plot_matrix_image",
    "plot_stack",
    "update_bandpass",
    "update_min_cc",
    "update_pick",
    "update_timewindow",
]

export_module_names(globals(), __name__)
