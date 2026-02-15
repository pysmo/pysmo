"""
Iterative Cross-Correlation and Stack (ICCS).

Warning:
    This module is being developed alongside a complete rewrite of
    [AIMBAT](https://github.com/pysmo/aimbat). Expect major changes until
    the rewrite is complete.

The ICCS[^1] method is an iterative algorithm to rapidly determine the best
fitting delay times between an arbitrary number of seismograms with minimal
involvement by a human operator. Instead of looking at individual seismograms,
parameters are set that control the algorithm, which then iteratively aligns
seismograms, or discards them from further consideration if they are of poor
quality.

The basic idea of ICCS, is that stacking all seismograms (aligned with respect
to an initial, and later improved, phase arrival pick) will lead to the
targeted phase arrival becoming visible in the stack. As the stack is generated
from all input seismograms, the phase arrival in the stack may be considered a
representation of the "best" mean arrival time. Each individual seismogram can
then be cross-correlated with the stack to determine a time shift that best
aligns them with the stack and thus each other.

The results of ICCS are similar to those of the MCCC[^2] method, while
also requiring fewer cross-correlations to be computed (each individual
seismogram is only cross-correlated with the stack, whereas in MCCC all
seismograms are cross-correlated with each other). ICCS is therefore
particularly useful to prepare data for a successful MCCC run (e.g. if the
initial picks are calculated rather than hand picked).

## Data requirements

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
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm. It should \
    be set to [`None`][None] initially. |
| [`select`][pysmo.tools.iccs.ICCSSeismogram.select] | Determines if a  \
    seismogram is used for the stack, and should therefore be [`True`][True] \
    initially. It is set to [`False`][False] for poor quality seismograms \
    automatically during a run if `autoselect` is [`True`][True]. Note that \
    this flag does _not_ exclude a seismogram from being cross-correlated with \
    the stack. Recovery is therefore possible and previously de-selected \
    seismograms may be selected again for the next iteration. |
| [`flip`][pysmo.tools.iccs.ICCSSeismogram.flip]     | Determines if the \
    seismogram data should be flipped (i.e. multiplied with -1) before using \
    it in the stack and cross-correlation. Can be automatically toggled when \
    `autoflip`is [`True`][True] during a [run][pysmo.tools.iccs.ICCS.__call__]. |

Two things worth mentioning:

- Because [`ICCSSeismogram`][pysmo.tools.iccs.ICCSSeismogram] is a subclass of
  [`Seismogram`][pysmo.Seismogram], it can be used anywhere a basic
  [`Seismogram`][pysmo.Seismogram] is expected.
- All actions performed only affect the attributes listed above. The original
  [`data`][pysmo.tools.iccs.MiniICCSSeismogram.data],
  [`begin_time`][pysmo.tools.iccs.MiniICCSSeismogram.begin_time], etc. are
  never modified.

## Execution flow

The diagram below shows execution flow, and how the above parameters are used
when the ICCS algorithm is executed (see [here][pysmo.tools.iccs.ICCS.__call__]
for parameters and default values):

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
Qual1["Toggle **select** attribute of seismograms based on correlation coefficient."]
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

Convergence is reached when the stack itself is not changing significantly
anymore between iterations. Typically this happens within a few iterations.

## Operator involvement

The ICCS algorithm relies on a few parameters that need to be adjusted by the
user. This module provides functions to visualise the stack and individual
seismograms (all at the same time), and to update the parameters based on
visual inspection.

[^1]: Lou, X., et al. “AIMBAT: A Python/Matplotlib Tool for Measuring
    Teleseismic Arrival Times.” Seismological Research Letters, vol. 84,
    no. 1, Jan. 2013, pp. 85–93, https://doi.org/10.1785/0220120033.
[^2]: VanDecar, J. C., and R. S. Crosson. “Determination of Teleseismic
    Relative Phase Arrival Times Using Multi-Channel Cross-Correlation and
    Least Squares.” Bulletin of the Seismological Society of America,
    vol. 80, no. 1, Feb. 1990, pp. 150–69,
    https://doi.org/10.1785/BSSA0800010150.
"""

from ..._utils import export_module_names
from ._iccs import ICCS
from ._types import MiniICCSSeismogram, ICCSSeismogram
from ._functions import (
    plot_seismograms,
    plot_stack,
    update_pick,
    update_timewindow,
    update_all_picks,
    update_min_ccnorm,
)

__all__ = [
    "ICCS",
    "ICCSSeismogram",
    "MiniICCSSeismogram",
    "plot_seismograms",
    "plot_stack",
    "update_pick",
    "update_timewindow",
    "update_all_picks",
    "update_min_ccnorm",
]

export_module_names(globals(), __name__)
