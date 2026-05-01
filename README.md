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

Pysmo is a seismology library built around a clean separation between data
storage and data processing. Processing functions are written against small,
focused interfaces — `Seismogram`, `Station`, `Event`, and so on — rather than
against specific classes. Any object that satisfies an interface can be used
with those functions directly.

The benefit is clearest when tackling a new problem. Data can be structured
however the problem demands, rather than adapted to fit a pre-existing class.
Functions specific to the problem can then consume that class directly, with
access to all its fields. More general operations — filtering, normalising,
resampling — are written against the interfaces and remain reusable across
every compatible type; pysmo ships with a library of these. Functions written
the same way for a specific project accumulate over time into a toolkit that
works across projects — and any that prove broadly useful are welcome as
contributions to pysmo.

Under the hood this is all standard Python typing, which means editors
understand it too: autocompletion is available on any argument declared as,
say, `Seismogram`, and mistakes — a missing attribute, a wrong return type —
are caught before any code is run. No special registration or inheritance is
required; if an object has the right attributes, it is compatible. Python's
typing system has advanced considerably in recent versions, and pysmo is
written to take full advantage of it — which is why older Python is not
supported.

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

The same holds for a bespoke class written from scratch for a particular
project, including fields that have no place in the protocol:

```python
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class MySeismogram:
    data: np.ndarray
    delta: pd.Timedelta
    begin_time: pd.Timestamp
    label: str

    @property
    def end_time(self) -> pd.Timestamp:
        # read-only: derived from begin_time, delta, and data
        return self.begin_time + self.delta * (len(self.data) - 1)

my_seis = MySeismogram(
    data=np.zeros(1000),
    delta=pd.Timedelta(seconds=0.01),
    begin_time=pd.Timestamp("2024-01-01", tz="UTC"),
    label="teleseismic_P",
)

print_info(my_seis)   # same function as above — no changes needed
detrend(my_seis)      # built-in functions work too
```
