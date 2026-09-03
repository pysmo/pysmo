<h1 align="center">pysmo</h1>

<p align="center">
<em>Documentation:</em> <a href="https://docs.pysmo.org" target="_blank">https://docs.pysmo.org</a>
</p>
<p align="center">
<em>Source Code:</em> <a href="https://github.com/pysmo/pysmo" target="_blank">https://github.com/pysmo/pysmo</a>
</p>

---

Pysmo is a seismology library. It is built around what processing code needs from
its data, not how those data are stored. Its functions are written against a
small set of `Protocol` types: `Seismogram`, `Station`, `Event`, and so on.
Protocols were added to Python in PEP 544. They are a major recent addition to
its type system.

A protocol is a contract. `Seismogram` lists the attributes a processing function
needs from a seismogram: the sample data, the sampling interval, the start time.
A function written against it can use nothing else. That keeps it easy to follow.
The same function also works with any object that meets the contract. That might
be pysmo's SAC-file wrapper, one of pysmo's own lightweight classes, or a class
written for a single study.

A study whose data fit no existing class can define its own. The class holds
exactly the fields the analysis needs. A function written for that study is typed
against the class directly and can use any of its fields. A function for wider
use is typed against a protocol instead. It works with any class that meets the
protocol. Extra fields on that class are ignored. Filtering, normalising, and
resampling work this way, and pysmo ships with a collection of such functions. A
study function that proves broadly useful can be retyped against a protocol and
contributed back.

A type checker understands the protocols directly. Most modern editors have one
built in, and it can also be run as a tool like mypy. A missing attribute or a
wrong return type is flagged as the code is written. Any argument annotated as
`Seismogram` gets autocompletion. Pysmo needs typing features from recent Python
releases, so older versions are unsupported.

## Quick Start

Pysmo also comes with ready-made classes and processing functions. The example
below uses two of those classes, some built-in functions, and one short function
defined on the spot. That last function works with both classes, unchanged.

```python
from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
from pysmo.functions import detrend, normalize, resample

# Read a SAC file
sac = SAC.from_file("myfile.sac")
seis = sac.seismogram  # satisfies the Seismogram protocol

# Process using built-in functions
detrend(seis)
normalize(seis)
resample(seis, seis.delta * 2)

# Write a function that works with any Seismogram implementation
def print_info(seismogram: Seismogram) -> None:
    print(f"Start: {seismogram.begin_time}")
    print(f"dt: {seismogram.delta}")

print_info(seis)  # works with SAC

# ...or create a lightweight seismogram from scratch
mini = MiniSeismogram(data=seis.data, delta=seis.delta, begin_time=seis.begin_time)
print_info(mini)  # works with MiniSeismogram too, same protocol
```

The same holds for a class written from scratch for one project. It can carry
fields the protocol has no place for:

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

print_info(my_seis)   # same function as above, no changes needed
detrend(my_seis)      # built-in functions work too
```
