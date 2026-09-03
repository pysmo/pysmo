---
icon: lucide/box
tags:
  - Classes
  - Usage
---

# External classes

The [tutorial](../first-steps/tutorial.md) and the section on
[mini classes](./mini-classes.md) show how straightforward it is to write a
bespoke class for use with pysmo. Sometimes an existing class is already in use,
though, perhaps because part of the processing happens in another framework.
This chapter covers that case.

## Does a class work with pysmo?

Pysmo types are typically simple, so an individual type usually has far fewer
attributes than any third-party class. The first step is deciding which types
the class needs to satisfy. Some will work as-is, some need extra work (a
different attribute name or data format), and some will never work, because the
data are not in the class at all.

!!! warning "Interface only, not implementation"

    Pysmo types define the interface, not the implementation. If the external class
    behaves differently from what a type expects (something as simple as different
    units, for instance), the mismatch will not show up as a type error.

### Yes

If the external class has the same attributes (name and type) as a given pysmo
type, it works as-is. To check, pass an instance to a function annotated with
the pysmo type and run [mypy](https://mypy.readthedocs.io), or watch the editor:
a matching class is accepted, and a near-miss is flagged at the attribute that
does not line up.

<!-- skip: start -->

```python
>>> from pysmo import Location
>>>
>>> def describe(location: Location) -> str:
...     return f"{location.latitude}, {location.longitude}"
...
>>> describe(my_external_object)  # mypy accepts this call if the class matches
'41.9, -87.6'
>>>
```

<!-- skip: end -->

This is most likely with simpler types like [`Location`][pysmo.Location], which
only requires `latitude` and `longitude` attributes of type [`float`][].

There is deliberately no need to gate this with a runtime check such as
[`isinstance`][] against the protocol (pysmo's protocols are not
`runtime_checkable`). Conformance is something the type checker proves, so the
workflow is to act on what mypy or the editor reports, before the code runs.
Runtime checks are still useful for a different question, covered in
[When a runtime check is genuinely needed](#when-a-runtime-check-is-genuinely-needed).

### Yes, with a tiny bit of work

The most common reason a class does not match a pysmo type is that the attribute
names differ. A class might store a station latitude in an attribute called
`stla` instead of `latitude`. A thin subclass can map the existing attributes to
the expected names using Python
[properties](https://docs.python.org/3/library/functions.html#property):

<!-- skip: next -->

```python
class MyExtendedClass(ExternalClass):
    @property
    def latitude(self) -> float:
        return self.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self.stla = value

    @property
    def longitude(self) -> float:
        return self.stlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        self.stlo = value
```

This pattern is lightweight: the subclass inherits everything from the original
class and only adds the property aliases needed for pysmo compatibility.
Changing an aliased attribute also changes the original, and vice versa. The
[`SAC`][pysmo.classes.SAC] API documentation has a concrete example.

### Yes, with a bit more work

Sometimes simple property aliases are not enough. This happens when:

- **The same class needs to match the same type more than once.** A class that
    stores both station and event coordinates cannot alias both to `latitude`
    and `longitude`; the names would clash.
- **The data format differs.** The external class might store a time as a float
    (seconds since some reference), while pysmo expects a
    [`datetime`][datetime.datetime] object.
- **An attribute is optional in the external class but required by the pysmo
    type.** The property getter then needs validation logic.

The approach here is a **helper class**: a small class that holds a reference to
the parent object and provides pysmo-compatible attribute access through
properties:

<!-- skip: next -->

```python
class StationLocation:
    def __init__(self, parent: ExternalClass) -> None:
        self._parent = parent

    @property
    def latitude(self) -> float:
        if self._parent.stla is None:
            raise ValueError("Station latitude is not set")
        return self._parent.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._parent.stla = value

    # longitude property omitted for brevity...
```

<!-- skip: next -->

```python
class EventLocation:
    def __init__(self, parent: ExternalClass) -> None:
        self._parent = parent

    @property
    def latitude(self) -> float:
        if self._parent.evla is None:
            raise ValueError("Event latitude is not set")
        return self._parent.evla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._parent.evla = value

    # longitude property omitted for brevity...
```

Both `StationLocation` and `EventLocation` match the `Location` type, and there
is no name clash because each helper class has its own namespace. Because they
reference the parent object, a change made through a helper class is reflected
in the parent, and vice versa.

The helper classes can then be added as attributes on a new class that inherits
from the external one:

<!-- skip: next -->

```python
class MyExtendedClass(ExternalClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.station_location = StationLocation(parent=self)
        self.event_location = EventLocation(parent=self)
```

Inheriting from `ExternalClass` is not required. Composition, holding the
external object as an attribute rather than subclassing it, works just as well:

<!-- skip: next -->

```python
class MyExtendedClass:
    def __init__(self, *args, **kwargs) -> None:
        self.external = ExternalClass(*args, **kwargs)
        self.station_location = StationLocation(parent=self.external)
        self.event_location = EventLocation(parent=self.external)
```

Composition is the better choice when `ExternalClass` has a large surface that
should not be exposed wholesale on `MyExtendedClass`. The `SAC` example below
does exactly this.

### No

Some data are simply not in the class. An ObsPy `Trace`, for example, carries no
station coordinates, so no adapter can make it satisfy
[`Station`][pysmo.Station]. An aliasing property or helper class can rename and
convert what is there; it cannot invent what is missing. In that case the type
is the wrong fit for that class, and the missing data have to come from
somewhere else.

## Examples

### `SAC`

The pysmo package itself uses this pattern for the [`SAC`][pysmo.classes.SAC]
class. The underlying [`SacIO`][pysmo.lib.io.SacIO] class manages file I/O and
exposes every SAC header field under its original name (`stla`, `evla`, `b`, and
so on). Those names do not match pysmo types, and station location, event
location, and seismogram data all coexist in one object. Exposing all ~99 raw
headers next to the curated attributes would invite name clashes, and worse,
silent errors where a raw header and a curated attribute share a name but carry
incompatible types and meaning (for example a raw time offset in seconds against
a `pandas.Timestamp` in UTC).

`SAC` solves this with the composition variant above: it holds a
[`SacIO`][pysmo.lib.io.SacIO] instance
([`SAC.native`][pysmo.classes.SAC.native]) rather than inheriting from it, and
adds helper-class attributes
([`station`][pysmo.classes.SAC.station]/[`event`][pysmo.classes.SAC.event]/
[`seismogram`][pysmo.classes.SAC.seismogram]/
[`timestamps`][pysmo.classes.SAC.timestamps]) that read from and write to it.
Only a small, deliberately curated surface (file I/O) is forwarded onto `SAC`
directly; seismogram data and sampling interval are reached via
[`SAC.seismogram`][pysmo.classes.SAC.seismogram], and the raw header names stay
reachable only via `SAC.native.<name>`, for anyone who specifically wants them,
rather than sitting on `SAC` itself under the same names as the curated
attributes. With that in place, pysmo functions work directly on the nested
objects:

```python
>>> from pysmo import Event, Seismogram, Station
>>> from pysmo.classes import SAC
>>>
>>> def begin_year(seismogram: Seismogram) -> int:
...     return seismogram.begin_time.year
...
>>> def station_id(station: Station) -> str:
...     return f"{station.network}.{station.name}"
...
>>> def origin_year(event: Event) -> int:
...     return event.time.year
...
>>> sac = SAC.from_file("example.sac")
>>> begin_year(sac.seismogram), station_id(sac.station), origin_year(sac.event)
(2010, 'IU.ANMO', 2010)
>>>
```

For more details, see the [`SAC`][pysmo.classes.SAC] API documentation.

### ObsPy's `Trace`

The [`SAC`][pysmo.classes.SAC] example above is pysmo's own code adapting
pysmo's own [`SacIO`][pysmo.lib.io.SacIO] class: useful for seeing the pattern
in use, but not literally an external class. A more realistic case for many
seismologists is waveform data already held as an
[ObsPy](https://docs.obspy.org/) `Trace` object, to be run through pysmo's
functions and tools without converting the whole workflow.

`Trace.stats` stores `starttime` as ObsPy's own `UTCDateTime` type (not
[`pandas.Timestamp`][]) and `delta` as a plain `float` in seconds (not
[`pandas.Timedelta`][]), so this needs the "attribute name and format differ"
treatment from above, not the free out-of-the-box case: the adapter needs
properties that convert between the two, not simple aliases. (`end_time` is not
read from `Trace.stats.endtime` at all; it is derived from `begin_time` and
`delta` instead, the same way [`Seismogram`][pysmo.Seismogram]'s `end_time` is
meant to be computed.)

```python title="trace_seismogram.py"
--8<-- "docs/snippets/external_classes/trace_seismogram.py"
```

<!-- skip: start -->

```python
>>> import numpy as np
>>> from obspy import Trace
>>> from pysmo.functions import detrend
>>> trace = Trace(
...     data=np.array([1.0, 2.0, 3.0, 2.0, 1.0]),
...     header={
...         "network": "XX",
...         "station": "TEST",
...         "location": "",
...         "channel": "HHZ",
...         "starttime": "2024-01-01T00:00:00",
...         "delta": 0.01,
...     },
... )
>>> trace_seis = TraceSeismogram(trace)
>>> detrend(trace_seis)  # detrend takes a Seismogram; mypy accepts trace_seis
>>> trace.data
array([...])
>>>
```

<!-- skip: end -->

With the setters in place, every [`pysmo.functions`][] and [`pysmo.tools`][]
call that takes a `Seismogram` works on `trace_seis` directly, including the
ones that mutate in place, like `detrend` above. Note what this adapter does
*not* attempt: `Trace.stats` has no latitude/longitude (that lives in ObsPy's
separate `Inventory` hierarchy, not on `Trace` itself), so `TraceSeismogram`
only ever satisfies `Seismogram`, never [`Station`][pysmo.Station]. Supply
station/event metadata separately, the same way
[`GeoCsvSeismogram.fetch()`][pysmo.classes.GeoCsvSeismogram.fetch] does.

!!! tip "Method vs function"

    Notice `detrend` is available in two different shapes above: ObsPy exposes it as
    a method on `Trace` (`trace.detrend(...)`), while pysmo exposes the same
    operation as a standalone function that takes a [`Seismogram`][pysmo.Seismogram]
    (`detrend(seismogram)`). That difference isn't incidental. A method bound to
    `Trace` only ever works on a `Trace` (or a subclass of it). A function written
    against the `Seismogram` protocol works on anything that satisfies it:
    `TraceSeismogram` here, [`SacSeismogram`][pysmo.classes.SacSeismogram], a
    [mini class](mini-classes.md), or any bespoke class written for the purpose.
    That's why the exact same [`detrend`][pysmo.functions.detrend] call works
    unchanged on the [`SAC`][pysmo.classes.SAC] example above and on `trace_seis`
    here, with no dispatch logic anywhere to make it happen. Targeting the protocol
    rather than one specific class is what makes every function in
    `pysmo.functions`/`pysmo.tools` reusable this way, and it isn't limited to
    pysmo's own functions: any function written against `Seismogram` gets the same
    property for free.

## When a runtime check is genuinely needed

The adapter patterns above are all about *conformance*: does this class speak a
pysmo type? That is a question for the type checker, not for [`isinstance`][].
One related task needs a different tool. At runtime, a collection holds a mix of
objects and two shapes need different treatment. Some station objects might
carry coordinates (satisfying [`Station`][pysmo.Station]) while others are
NSLC-only (satisfying [`StationCode`][pysmo.StationCode] but not `Station`, as a
seismogram read straight from miniSEED is), and the code needs to branch on
which it has.

Write that branch as a [`TypeIs`][typing.TypeIs] guard. It narrows the type for
the type checker in both branches, and names exactly what is being checked:

```python
>>> from typing import TypeIs
>>> from pysmo import MiniStation, MiniStationCode, Station, StationCode
>>>
>>> def has_location(sta: StationCode) -> TypeIs[Station]:
...     return hasattr(sta, "latitude") and hasattr(sta, "longitude")
...
>>> stations: list[StationCode] = [
...     MiniStation(
...         name="ANMO", network="IU", location="00", channel="BHZ",
...         latitude=34.95, longitude=-106.46,
...     ),
...     MiniStationCode(name="COLA", network="IU", location="00", channel="BHZ"),
... ]
>>> [sta.name for sta in stations if has_location(sta)]
['ANMO']
>>>
```

This is for runtime dispatch over mixed data, **not** for checking whether a
class conforms to a protocol. That stays a type-checker job.

## Beyond adapting existing classes

The chapter so far is about making an external class usable with pysmo's
*existing* functions, in Python. That is useful, but it undersells what a pysmo
type actually is.

This chapter has already built that twice, in two different shapes, without
naming it. The helper-class approach builds a narrow view as a separate object
that reads from, and writes back to, a richer parent.
[`SacSeismogram`][pysmo.classes.SacSeismogram] is a real example: `SAC` carries
the full complexity of a SAC file's header, `SacSeismogram` exposes only what
[`Seismogram`][pysmo.Seismogram] needs. The thin-subclass approach does not even
need a separate object: a single bespoke class can carry its own extra
attributes directly, alongside the ones a protocol requires, and still be handed
to any function expecting that protocol unchanged. Either way, the "rich" and
"narrow" views are not two objects with data copied between them; they are two
readings of the same one.

This is a general pattern, not something specific to these two examples. The
same object can be two different things at once, depending on what is looking at
it. To the code that owns it, a seismogram can carry arbitrarily rich,
problem-specific state: processing history, quality flags, picks, provenance,
whatever the task needs. To a function written against `Seismogram`, that same
object is just `begin_time`, `data`, `delta`, nothing more. Both are true at
once, of the same instance: the type does not strip anything away, it only
describes which part of the object a given piece of code has committed to
relying on.

The narrow view is the more interesting half of that pair. A type like
`Seismogram` is not really a Python feature; it is a minimal specification of
what a seismogram fundamentally needs to be, arrived at by asking what
processing functions actually require rather than what any one class happens to
expose (see [What should become a type?](types.md#what-should-become-a-type)).
[`Protocol`][typing.Protocol] is simply the notation this specification is
written in today. The definition itself (begin time, data, sampling interval,
nothing more) would translate just as directly into a struct in C or Fortran, a
database schema, or a paragraph of prose. It does not depend on Python, or on
pysmo, to remain true.

That distinction matters over a project's lifetime. Libraries and file formats
change (sometimes for good reasons, sometimes because tooling fashions shift),
and code written directly against one specific class inherits that churn. Code
written against a well-considered, minimal interface mostly does not: only the
adaptation layer at the boundary needs to change, not the logic behind it. The
same holds on a smaller scale. Moving a slow step like
[`mccc`][pysmo.tools.signal.mccc] from Python to a compiled language for speed
is a good example. The hard part is never translating syntax; it is working out
what the minimal data model needs to be. If that work is already done, captured
as a small, deliberate interface rather than smeared across whatever attributes
a particular class happened to expose, the move means reimplementing the
interface and its adapters in the new language's idiom, not re-deriving the
whole data model from scratch.

External change is not the only unpredictable thing. How complex the class
supporting a particular problem will need to become is rarely clear in advance.
A bespoke class does not have to mean a dataclass with a few extra attributes;
that is the simplest case, not the only one. What starts that way can, as a
project's real requirements surface, turn into something far more involved.
[AIMBAT](https://github.com/pysmo/aimbat) (an arrival-time picking package built
on pysmo) shows both ends of that range. Its first version had nowhere else to
put processing state, so it stored things like filter parameters directly in
SAC's generic `user6`/`user7`/`kuser1`/`kuser2` header fields, which have no
defined meaning of their own and were repurposed because nothing better was
available. (It is also why old AIMBAT-processed SAC files can carry
oddly-populated header fields that are confusing to decode later.) Current
AIMBAT solves the same problem properly: its seismogram objects are backed by a
SQL database, with `begin_time` and `delta` stored as ordinary table columns and
`data` fetched from a separate table only when needed. That split pays off
concretely: changing a pick or a sampling interval is a small database update,
not a read of the whole waveform file. With a SAC file read directly, no such
distinction is available: updating one value means touching the entire
seismogram. None of this can be planned for up front, and it does not need to
be. The protocol boundary does not ask the rich side to stay simple, or to stay
anything in particular, only that [`begin_time`][pysmo.Seismogram.begin_time],
[`data`][pysmo.Seismogram.data], and [`delta`][pysmo.Seismogram.delta] keep
meaning what they always meant. The processing logic on the other side of that
boundary never has to change, no matter how unrecognisable the rich side
becomes.

Pysmo's types are one attempt at doing this work for seismology. The same
exercise is worth doing for whatever is specific to a given project.
