# flake8: noqa: E402
"""Iterative Cross-Correlation and Stack (ICCS).

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

The basic idea of ICCS is that stacking all seismograms (aligned with respect
to an initial, and later improved, phase arrival pick) will lead to the
targeted phase arrival becoming visible in the stack. As the stack is generated
from all input seismograms, the phase arrival in the stack may be considered a
representation of the "best" mean arrival time. Each individual seismogram can
then be cross-correlated with the stack to determine a time shift that best
aligns them with the stack and thus each other.

The results of ICCS are similar to those produced by the
[`mccc`][pysmo.tools.signal.mccc] algorithm, while also requiring fewer
cross-correlations to be computed (each individual seismogram is only
cross-correlated with the stack, whereas in MCCC all seismograms are
cross-correlated with each other). ICCS is therefore particularly useful to
prepare data for a successful MCCC run (e.g. if the initial picks are
calculated rather than hand picked).

[^1]: Lou, X., et al. “AIMBAT: A Python/Matplotlib Tool for Measuring
    Teleseismic Arrival Times.” Seismological Research Letters, vol. 84,
    no. 1, Jan. 2013, pp. 85–93, <https://doi.org/10.1785/0220120033>.

## Data requirements

The [`iccs`][pysmo.tools.iccs] module requires that seismograms contain extra
attributes specific to the ICCS method. Hence it provides a protocol class
([`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram]) and corresponding Mini
class ([`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram]). In
addition to the common attributes of a [`Seismogram`][pysmo.Seismogram] in
pysmo, the following parameters are required:

| Attribute                                          | Description |
| -------------------------------------------------- | ----------- |
| [`t0`][pysmo.tools.iccs.IccsSeismogram.t0]         | Initial pick (typically \
    computed). Serves as input only when `t1` is not set. |
| [`t1`][pysmo.tools.iccs.IccsSeismogram.t1]         | Improved pick. \
    Serves as both input (if not [`None`][]) and output (always) when \
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm. It should \
    be set to [`None`][] initially. |
| [`select`][pysmo.tools.iccs.IccsSeismogram.select] | Determines if a  \
    seismogram is used for the stack, and should therefore be [`True`][] \
    initially. It is set to [`False`][] for poor quality seismograms \
    automatically during a run if `autoselect` is [`True`][]. Note that \
    this flag does _not_ exclude a seismogram from being cross-correlated with \
    the stack. Recovery is therefore possible and previously de-selected \
    seismograms may be selected again for the next iteration. |
| [`flip`][pysmo.tools.iccs.IccsSeismogram.flip]     | Determines if the \
    seismogram data should be flipped (i.e. data are multiplied with -1) when \
    using it in the stack and cross-correlation. Can be automatically toggled \
    when `autoflip` is [`True`][] during a \
    [run][pysmo.tools.iccs.ICCS.__call__]. |

## Ephemeral seismograms

As the ICCS algorithm operates on a window around the targeted phase arrival,
only a small portion of the input seismogram data are used. These smaller
portions are generated on the fly in two ways, each with a causally-filtered
counterpart used by picking-oriented tools. The ICCS algorithm itself
always runs on the zero-phase variant, as does MCCC, regardless of which
one is currently displayed — see
[`ICCS.corners`][pysmo.tools.iccs.ICCS.corners], which sets the zero-phase
filter's order and from which the causal variant's own order is derived:

- **Cross-correlation seismograms** are used for the execution of the ICCS
  algorithm. They consist of the windowed portion around the phase arrival and
  a tapered ramp up and down *outside* the window.
- **Context seismograms** are used to provide extra context. They consist of a
  broader window around the phase arrival, and without any tapering applied.

Both share common processing steps, and are used to create a corresponding
stack. As they are completely reproducible, they only exist for the lifetime
of the [`ICCS`][pysmo.tools.iccs.ICCS] instance that contains the input
[`seismograms`][pysmo.tools.iccs.ICCS.seismograms] and parameters used in
their creation. Changing any of the parameters will lead to automatic
regeneration of the ephemeral seismograms, however, as mutations of a list
cannot be detected, adding or removing seismograms from the list will _not_
trigger regeneration. In that case, clearing the cache must be done manually by
calling [`clear_cache`][pysmo.tools.iccs.ICCS.clear_cache].

!!! tip "Both types support interactive picking"

    Both types can be used for visualisation purposes. It is therefore possible
    to e.g. pick an updated arrival in the cross-correlation seismograms, and
    pick new time window boundaries in the context seismograms.

## Execution flow

The diagram below shows execution flow, and how the above parameters are used
when the ICCS algorithm is executed (see
[`ICCS.__call__`][pysmo.tools.iccs.ICCS.__call__] for parameters and default
values):

```mermaid
flowchart TD
Start(["`IccsSeismograms with initial parameters.`"])
Stack0["`Generate windowed seismograms and create stack from them.`"]
C["`Cross-correlate windowed seismograms with stack to obtain updated picks and normalised correlation coefficients.`"]
FlipQ{"`Is **autoflip**
True?`"}
Flip["`Toggle **flip** attribute of seismograms with negative correlation coefficients.`"]
QualQ{"`Is **autoselect**
True?`"}
Qual1["`Toggle **select** attribute of seismograms based on correlation coefficient.`"]
Stack1["`Recompute windowed seismograms and stack with updated parameters.`"]
H{"`Convergence
criteria met?`"}
I{"`Maximum
iterations
reached?`"}
End(["`IccsSeismograms with updated **t1**, **flip**, and **select** parameters.`"])
Start --> Stack0 --> C --> FlipQ -->|No| QualQ -->|No| Stack1 --> H -->|No| I -->|No| C
FlipQ -->|Yes| Flip --> QualQ
QualQ -->|Yes| Qual1 -->  Stack1
H -->|Yes| End
I -->|Yes| End
```

Convergence is reached when the stack is no longer changing significantly
between iterations. Typically this happens within a few iterations.

## Operator involvement

Using ICCS involves two distinct kinds of iteration, easy to conflate but
serving different purposes:

- **Algorithmic iteration**, shown in the diagram above, is automatic and
  internal to a single call of an [`ICCS`][pysmo.tools.iccs.ICCS] instance.
  Each iteration cross-correlates seismograms with the current stack, updates
  picks (and, optionally, `flip`/`select`), and recomputes the stack, stopping
  once the stack converges or `max_iter` is reached. The operator has no part
  in this process; `max_iter` only bounds it.
- **Operator iteration** is the repeated refinement of the *parameters* given
  to the algorithm, across repeated calls. After a call, the operator inspects
  the resulting stack and individual seismograms visually, and may decide
  that the pick, time window, minimum correlation coefficient, or bandpass
  filter need adjusting — e.g. narrowing the time window once the phase
  arrival is clearly visible, or raising `min_cc` once obviously poor
  seismograms have been excluded. This module provides interactive functions
  for making exactly these adjustments —
  [`update_pick`][pysmo.tools.iccs.update_pick],
  [`update_timewindow`][pysmo.tools.iccs.update_timewindow],
  [`update_min_cc`][pysmo.tools.iccs.update_min_cc], and
  [`update_bandpass`][pysmo.tools.iccs.update_bandpass] — after which the
  instance is called again. How many times this happens, and when to stop, is
  entirely up to the operator; nothing in the algorithm tracks or limits it.

!!! tip "AIMBAT"

    [AIMBAT](https://github.com/pysmo/aimbat) builds this operator loop into a
    full interactive application, managing parameter snapshots and the wider
    ICCS → QC → MCCC pipeline, rather than requiring it to be scripted by hand
    as in the example below.

## Basic example

This example starts with six synthetic seismograms, each built from the
same underlying pulse (an idealised phase arrival) buried in independent
background noise, so the perturbations introduced below remain a large
enough fraction of the signal to be clearly visible; with the dozens of
stations a real array typically provides, the same perturbations would be
a much smaller fraction of the total, and their effect correspondingly
harder to see. Using synthetic data instead of a real recording keeps this
walkthrough fully self-contained and its outcome exactly reproducible:

```python
>>> import numpy as np
>>> import pandas as pd
>>> from pysmo.tools.iccs import MiniIccsSeismogram
>>>
>>> def ricker(points: int, width: float) -> np.ndarray:
...     # a "Mexican hat" wavelet, standing in for a real phase arrival
...     t = np.arange(points) - (points - 1) / 2
...     return (
...         2
...         / (np.sqrt(3 * width) * np.pi**0.25)
...         * (1 - (t / width) ** 2)
...         * np.exp(-(t**2) / (2 * width**2))
...     )
...
>>> pulse = ricker(200, 12)
>>> pulse /= np.abs(pulse).max()
>>>
>>> npts = 2400
>>> pick_index = 1200
>>> delta = pd.Timedelta(seconds=0.05)
>>> begin_time = pd.Timestamp("2024-01-01", tz="UTC")
>>> t0 = begin_time + pick_index * delta
>>>
>>> rng = np.random.default_rng(42)
>>> seismograms = []
>>> for _ in range(6):
...     data = rng.normal(scale=0.03, size=npts)
...     data[pick_index - 100 : pick_index + 100] += pulse
...     seismograms.append(
...         MiniIccsSeismogram(begin_time=begin_time, delta=delta, data=data, t0=t0)
...     )
...
>>>
```

To illustrate the different modes of running the ICCS algorithm, the data
and picks are then degraded. Every seismogram but the first has its pick
shifted by a few seconds, varied enough that no phase emergence survives
naive stacking on the raw picks. The first seismogram has its polarity
reversed instead, and a seventh, entirely synthetic seismogram of random
noise (no pulse at all) is appended:

```python
>>> from copy import deepcopy
>>>
>>> # change the sign of the data in the first seismogram
>>> seismograms[0].data *= -1
>>>
>>> # shift the remaining picks by varying amounts, in both directions
>>> shifts = [-4, 4, -6, 6, -3]
>>> for seismogram, shift in zip(seismograms[1:], shifts):
...     seismogram.t0 += pd.Timedelta(seconds=shift)
...
>>>
>>> # create a seismogram with completely random data
>>> iccs_random: MiniIccsSeismogram = deepcopy(seismograms[-1])
>>> iccs_random.data = np.random.default_rng(1).normal(scale=0.3, size=npts)
>>> seismograms.append(iccs_random)
>>>
```

An [`ICCS`][pysmo.tools.iccs.ICCS] instance can now be created and used to
plot the initial [`stack`][pysmo.tools.iccs.ICCS.stack] and
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
>>> if savedir:
...     fig.savefig(savedir / "iccs_stack_initial.png", transparent=True)
...     plt.close("all")
...     plt.style.use("dark_background")
...     fig, ax = plot_stack(iccs, context=False)
...     fig.savefig(savedir / "iccs_stack_initial-dark.png", transparent=True)
...     plt.style.use("default")
>>>
```
-->

![Initial stack](../../../images/sybil/iccs_stack_initial.png#only-light){ loading=lazy }
![Initial stack](../../../images/sybil/iccs_stack_initial-dark.png#only-dark){ loading=lazy }

No phase emergence is visible in the stack yet. To run the ICCS
algorithm, simply call (execute) the ICCS instance:

```python
>>> convergence_list = iccs()  # this runs the ICCS algorithm and returns
>>>                            # a list of the convergence value after each
>>>                            # iteration.
>>> fig, ax = plot_stack(iccs, context=False)
>>>
```

<!-- invisible-code-block: python
```
>>> def _annotate_flipped(ax):
...     # find the trace whose trough is deepest relative to its own
...     # peak -- the visual signature of the reversed-polarity
...     # seismogram, for readers viewing the saved image
...     candidates = [
...         line
...         for line in ax.lines
...         if line.get_label() != "Stack" and len(line.get_xdata()) > 2
...     ]
...     flipped_line = max(
...         candidates,
...         key=lambda line: -min(line.get_ydata()) - max(line.get_ydata()),
...     )
...     idx = np.argmin(flipped_line.get_ydata())
...     x = flipped_line.get_xdata()[idx]
...     y = flipped_line.get_ydata()[idx]
...     ax.annotate(
...         "reversed polarity",
...         xy=(x, y),
...         xytext=(x + 4, y + 0.5),
...         ha="left",
...         arrowprops={"arrowstyle": "->"},
...     )
...
>>> if savedir:
...     _annotate_flipped(ax)
...     fig.savefig(savedir / "iccs_stack_first_run.png", transparent=True)
...     plt.close("all")
...     plt.style.use("dark_background")
...     fig, ax = plot_stack(iccs, context=False)
...     _annotate_flipped(ax)
...     fig.savefig(savedir / "iccs_stack_first_run-dark.png", transparent=True)
...     plt.style.use("default")
>>>
```
-->

![Stack after first run](../../../images/sybil/iccs_stack_first_run.png#only-light){ loading=lazy }
![Stack after first run](../../../images/sybil/iccs_stack_first_run-dark.png#only-dark){ loading=lazy }

Despite the random noise seismogram, the phase arrival is now visible in
the stack, and most correlation coefficients are high. The noise
seismogram's correlation is clearly the lowest, but the
reversed-polarity seismogram's is only mediocre rather than obviously
bad — precisely the case [`ICCS`][pysmo.tools.iccs.ICCS] is designed to
catch automatically, since a real dataset of hundreds of seismograms
cannot be checked individually by eye. It is annotated above: the trace
whose largest excursion points downward rather than upward, easy to miss
among the others at a glance but a useful hint once you know to look for
it. Running ICCS again with `autoflip=True` checks the reversed-polarity
hypothesis for every seismogram and finds a substantially better fit for
this one:

```python
>>> _ = iccs(autoflip=True)
>>> fig, ax = plot_stack(iccs, context=False)
>>>
```

<!-- invisible-code-block: python
```
>>> if savedir:
...     fig.savefig(savedir / "iccs_stack_autoflip.png", transparent=True)
...     plt.close("all")
...     plt.style.use("dark_background")
...     fig, ax = plot_stack(iccs, context=False)
...     fig.savefig(savedir / "iccs_stack_autoflip-dark.png", transparent=True)
...     plt.style.use("default")
>>>
```
-->

![Stack after run with autoflip](../../../images/sybil/iccs_stack_autoflip.png#only-light){ loading=lazy }
![Stack after run with autoflip](../../../images/sybil/iccs_stack_autoflip-dark.png#only-dark){ loading=lazy }

The previously-mediocre seismogram is now among the best-fitting of all
seven. The noise seismogram is unaffected — no polarity reversal fixes
what is not a real signal — and remains the clear outlier. Running ICCS
again with `autoselect=True` deselects seismograms whose fit is
genuinely poor, rather than merely reversed:

```python
>>> _ = iccs(autoselect=True)
>>> [seismogram.select for seismogram in iccs.seismograms]
[True, True, True, True, True, True, False]
>>> fig, ax = plot_stack(iccs, context=False)
>>>
```

<!-- invisible-code-block: python
```
>>> if savedir:
...     fig.savefig(savedir / "iccs_stack_autoselect.png", transparent=True)
...     plt.close("all")
...     plt.style.use("dark_background")
...     fig, ax = plot_stack(iccs, context=False)
...     fig.savefig(savedir / "iccs_stack_autoselect-dark.png", transparent=True)
...     plt.style.use("default")
>>>
```
-->

![Stack after run with autoselect](../../../images/sybil/iccs_stack_autoselect.png#only-light){ loading=lazy }
![Stack after run with autoselect](../../../images/sybil/iccs_stack_autoselect-dark.png#only-dark){ loading=lazy }

Only the noise seismogram is deselected; every real seismogram,
including the one that needed flipping, now contributes to the stack.

The stack above still has room for improvement: the pick sits several
seconds off the main pulse, and the default ±15 s time window extends well
past the pulse's energy into background noise that only degrades the
cross-correlation. See [operator iteration](#operator-involvement) above
for how to refine these before, say, proceeding to MCCC.
"""

from ..._utils import export_module_names
from ._iccs import ICCS
from ._types import IccsResult, IccsSeismogram, McccResult, MiniIccsSeismogram
from .plot import (
    plot_matrix_image,
    plot_stack,
    update_bandpass,
    update_min_cc,
    update_pick,
    update_timewindow,
)

__all__ = [
    "ICCS",
    "IccsSeismogram",
    "IccsResult",
    "McccResult",
    "MiniIccsSeismogram",
    "plot_matrix_image",
    "plot_stack",
    "update_bandpass",
    "update_min_cc",
    "update_pick",
    "update_timewindow",
]

export_module_names(globals(), __name__)
