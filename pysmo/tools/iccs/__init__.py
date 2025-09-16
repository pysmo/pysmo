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

The results of ICCS are are similar to those of the the MCCC[^2] method, while
also requiring fewer cross-correlations to be computed (each individual
seismogram is only cross-correlated with the stack, whereas in MCCC all
seismograms are cross-correlated with each other). ICCS is therefore
particularly useful to perepare data for a successful MCCC run (e.g. if the
initial picks are calculated rather than hand picked).

The [`iccs`][pysmo.tools.iccs] module requires seismograms containing extra
attributes specific to the ICCS method. Hence it provides a protocol class
([`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram]) and corresponding Mini
class ([`MiniICCSSeismogram`][pysmo.tools.iccs.MiniICCSSeismogram]) for that
purpose. In addition to the common attributes of a
[`Seismogram`][pysmo.Seismogram] in pysmo, the following parameters are
required:

| Attribute                                          | Description |
| -------------------------------------------------- | ----------- |
| [`t0`][pysmo.tools.iccs.ICCSSeismogram.t0]         | Initial pick (typically \
    computed). Serves as input only when `t1` is not set. |
| [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1]         | Improved pick. \
    Serves as both input (if not [`None`][None]) and output (always) when \
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm. |
| [`select`][pysmo.tools.iccs.ICCSSeismogram.select] | Determines if a  \
    seismogram should be used for the stack. Can be automatically set when \
    `autoselect`is [`True`][True] during a run. |
| [`flip`][pysmo.tools.iccs.ICCSSeismogram.flip]     | Determines if the \
    seismogram data should be flipped (i.e. multiplied with -1) before using \
    it in the stack and cross-correlation. Can be automatically set when \
    `autoflip`is [`True`][True] during a run. |

The diagram below shows execution flow, and how the above parameters are used
when the ICCS algorithm is executed (see [here][pysmo.tools.iccs.ICCS.__call__]
for parameters and default values)':

```mermaid
flowchart TD
Start(["ICCSSeismograms with initial parameters."])
Stack0["Generate windowed seismograms and create stack from them."]
C["Cross-correlate windowed seismograms with stack to obtain updated picks and normalised correlation coefficients."]
FlipQ{"Is **autoflip**
True?"}
Flip["Toggle **flip** attribute of seismograms with negative correlation coefficients."]
QualQ{"Is **autoselect**
True?"}
Qual1["Set **select** attribute of seismograms to False for poor quality seismograms."]
Stack1["Recompute windowed seismograms and stack with updated parameters."]
H{"Convergence
criteria met?"}
I{"Maximum
iterations
reached?"}
End(["ICCSSeismograms with updated **t1**, **flip**, and **select** parameters."])
Start --> Stack0 --> C --> FlipQ -->|No| QualQ -->|No| Stack1 --> H -->|No| I -->|No| C
FlipQ -->|Yes| Flip --> QualQ
QualQ -->|Yes| Qual1 -->  Stack1
H -->|Yes| End
I -->|Yes| End
```

[^1]: Lou, X., et al. “AIMBAT: A Python/Matplotlib Tool for Measuring
    Teleseismic Arrival Times.” Seismological Research Letters, vol. 84,
    no. 1, Jan. 2013, pp. 85–93, https://doi.org/10.1785/0220120033.
[^2]: VanDecar, J. C., and R. S. Crosson. “Determination of Teleseismic
    Relative Phase Arrival Times Using Multi-Channel Cross-Correlation and
    Least Squares.” Bulletin of the Seismological Society of America,
    vol. 80, no. 1, Feb. 1990, pp. 150–69,
    https://doi.org/10.1785/BSSA0800010150.
"""

from ._iccs import ICCS
from ._types import MiniICCSSeismogram, ICCSSeismogram
from ._functions import (
    plotstack,
    stack_pick,
    stack_timewindow,
    update_all_picks,
    select_min_ccnorm,
)

__all__ = [
    "ICCS",
    "ICCSSeismogram",
    "MiniICCSSeismogram",
    "plotstack",
    "stack_pick",
    "stack_timewindow",
    "update_all_picks",
    "select_min_ccnorm",
]
