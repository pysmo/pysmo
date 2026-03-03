<h1 align="center">pysmo</h1>

<div align="center">
<a href="https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml" target="_blank">
<img src="https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml/badge.svg" alt="Test Status">
</img></a>
<a href="https://github.com/pysmo/pysmo/actions/workflows/build.yml" target="_blank">
<img src= "https://github.com/pysmo/pysmo/actions/workflows/build.yml/badge.svg" alt="Build Status">
</img></a>
<a href="https://pysmo.readthedocs.io/en/latest/?badge=latest" target="_blank">
<img src="https://readthedocs.org/projects/pysmo/badge/?version=latest" alt="Documentation Status">
</img></a>
<a href="https://codecov.io/gh/pysmo/pysmo" target="_blank">
<img src="https://codecov.io/gh/pysmo/pysmo/branch/master/graph/badge.svg?token=ZsHTBN4rxF" alt="codecov">
</img></a>
<a href="https://pypi.org/project/pysmo/" target="_blank">
<img src="https://img.shields.io/pypi/v/pysmo" alt="PyPI">
</img></a>
<a href="https://pypi.org/project/pysmo/" target="_blank">
<img src="https://img.shields.io/pypi/pyversions/pysmo" alt="Python Versions">
</img></a>
<a href="https://github.com/pysmo/pysmo/blob/master/LICENSE" target="_blank">
<img src="https://img.shields.io/github/license/pysmo/pysmo" alt="License">
</img></a></div>

<p align="center">
<em>Documentation:</em> <a href="https://docs.pysmo.org" target="_blank">https://docs.pysmo.org</a>
</p>
<p align="center">
<em>Source Code:</em> <a href="https://github.com/pysmo/pysmo" target="_blank">https://github.com/pysmo/pysmo</a>
</p>

---

Most seismology libraries hand you a single large object — waveform samples,
station coordinates, and event parameters all bundled together. This is a
common pattern, but it sidesteps a question worth asking: *what is a
seismogram, actually?* Not a file format. A seismogram is a time series:
samples, a sampling interval, and a start time. A station is a named
geographic position. These are narrow, precise concepts, and modern Python
gives us the vocabulary to express them exactly — `Protocol` classes,
`Annotated` types, structural subtyping. Pysmo follows that structure: each
type maps to a real scientific concept, concrete classes enforce correctness
at construction, and file-format adapters expose only what a concept actually
needs.

When a function declares exactly which concept it needs, your editor knows too — autocomplete is precise, type errors
surface before runtime, and a function signature is enough to understand what
it consumes. Narrower types also dissolve a question that haunts any large
bundled object: what counts as data, and what is metadata? The answer depends
on what you are doing, not on the file format that happens to store it. The
conventional response is to make fields optional: bundle everything into one
object, set unused attributes to `None`, and let callers decide what matters.
This sidesteps the design question but compounds the practical one — a station
coordinate of `None` is no more meaningful than a `float` with the value
`"abc"`, and the error surfaces far from where the bad assumption was made.
When types reflect scientific concepts directly, the boundaries emerge from the
science instead. Code written against narrow interfaces is reusable for the
same reason: a function that accepts a protocol works with any conforming
object — a file parser, a hand-written dataclass, or a lightweight instance
created in a notebook — without modification.

The same logic also narrows the gap between user code and library. Pysmo
ships with a collection of processing tools — though that is not what it is
fundamentally about. They exist because the same design applies: any function
written against pysmo's protocols is compatible with every conforming object,
and therefore useful beyond its original context. The tools can be used
directly or as building blocks for something larger. Any well-written
pysmo-compatible code is a reasonable candidate for inclusion in the library.
Contributions are always welcome, though more often the consequence is
simpler: code written for one project finds itself useful in the next.

## Quick Start

Pysmo includes concrete classes and processing functions that put everything
above into practice. Below, two of those classes are used alongside built-in
functions and a simple user-defined one — the latter works with both without
any modification, which is the point.

```python
from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
from pysmo.functions import detrend, normalize, resample

# Read a SAC file — access seismogram data via protocol-typed views
sac = SAC.from_file("myfile.sac")
seis = sac.seismogram  # satisfies the Seismogram protocol

# Process using built-in functions
detrend(seis)
normalize(seis)
resample(seis, seis.delta * 2)

# Write a function that works with ANY Seismogram implementation
def print_info(seismogram: Seismogram) -> None:
    print(f"Start: {seismogram.begin_time}")
    print(f"dt: {seismogram.delta}")

print_info(seis)  # works with SAC

# ...or create a lightweight seismogram from scratch
mini = MiniSeismogram(data=seis.data, delta=seis.delta, begin_time=seis.begin_time)
print_info(mini)  # works with MiniSeismogram too — same protocol
```

The design shifts the question from what a class provides to what a function
needs. Rather than being bound by what a library class exposes, you are free
to define bespoke classes for a particular project, and they will work with
any function whose protocol they satisfy.

```python
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class MySeismogram:
    data: np.ndarray
    delta: pd.Timedelta
    begin_time: pd.Timestamp
    my_attribute: str

    @property
    def end_time(self) -> pd.Timestamp:
        # read-only: derived from begin_time, delta, and data
        return self.begin_time + self.delta * (len(self.data) - 1)

my_seis = MySeismogram(
    data=np.zeros(1000),
    delta=pd.Timedelta(seconds=0.01),
    begin_time=pd.Timestamp("2024-01-01", tz="UTC"),
    my_attribute="hello world",
)

print_info(my_seis)   # same function as above — no changes needed
detrend(my_seis)      # built-in functions work too
```
