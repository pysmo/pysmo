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

Pysmo leverages modern Python (3.12+) to bring type safety and clean
abstractions to seismology code.

### Protocol-based design

Pysmo defines its core types —
[`Seismogram`](https://docs.pysmo.org), [`Station`](https://docs.pysmo.org),
[`Event`](https://docs.pysmo.org) — as **Protocol classes** (structural
subtyping). Any object that has the right attributes satisfies the protocol;
no inheritance required. This means pysmo functions work with *your* classes
out of the box, as long as they look like the right type.

### Runtime validation with attrs and beartype

Pysmo's concrete "Mini" classes (e.g. `MiniSeismogram`) are built with
[attrs](https://www.attrs.org) and validated at runtime by
[beartype](https://beartype.readthedocs.io). Fields carry validators and
converters — a `datetime` without `tzinfo=UTC` or a negative sampling
interval is rejected immediately, not silently propagated.

### Separation of storage and processing

File formats bundle many fields together. Pysmo splits them into narrowly
scoped protocol types so that processing code stays simple, testable, and
reusable across projects. A `SAC` object exposes `.seismogram`, `.station`,
and `.event` views — each satisfying the corresponding protocol — without
coupling your analysis code to the SAC format.

## Quick Start

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
    print(f"Samples: {len(seismogram)}, dt: {seismogram.delta}")

print_info(seis)  # works with SacSeismogram

# ...or create a lightweight seismogram from scratch
mini = MiniSeismogram(data=seis.data, delta=seis.delta, begin_time=seis.begin_time)
print_info(mini)  # works with MiniSeismogram too — same protocol
```

## Key Concepts

| Concept | Python Feature | Pysmo Example |
|---|---|---|
| Structural subtyping | `Protocol` + `@runtime_checkable` | `Seismogram`, `Station`, `Event` |
| Validated data classes | `attrs` with field validators | `MiniStation(name="STA", latitude=48.2, ...)` |
| Runtime type checking | `beartype` + `Annotated` types | `PositiveTimedelta`, `UnitFloat` |
| Generic functions | PEP 695 type parameters | `def crop[T: Seismogram](...) -> T` |
| Format adapters | Descriptors + `__set_name__` | `SAC.seismogram`, `SAC.station` |

## Why Protocols?

Traditional seismology libraries often require you to inherit from a base
class or convert data into a library-specific format. Pysmo takes a different
approach: functions accept any object that satisfies a protocol. You can use
pysmo functions with your own classes — no subclassing, no format conversion,
no vendor lock-in.

```python
# Your own class — no pysmo base class needed
@dataclass
class MySeismogram:
    begin_time: datetime
    delta: timedelta
    data: np.ndarray
    def __len__(self) -> int:
        return len(self.data)

# pysmo functions just work
from pysmo.functions import detrend
detrend(MySeismogram(...))  # satisfies the Seismogram protocol
```
