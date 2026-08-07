---
icon: lucide/box
tags:
- Classes
- Usage
---
# External Classes

The [tutorial](../first-steps/tutorial.md) and the section on
[mini classes](./mini-classes.md) show how easy it is to write a bespoke class
for use with pysmo. However, you may already be committed to using an existing
class (e.g. because you need to do some processing in another framework). This
chapter discusses this scenario.

## Does a class work with pysmo?

Before answering this question, remember that pysmo types are typically very
simple. Most likely an individual type will contain way fewer attributes than
any third-party class. You must therefore decide which types you want to use
with the class. Some may work out-of-the-box, others may require some extra
work (e.g. because the attribute name or data format are different), and some
will never work (perhaps because the necessary data are not in the class to
begin with).

!!! warning

    Keep in mind that pysmo types merely define the interface, not the
    implementation. If the external class does something internally that
    differs from the expected behaviour (this could be something as simple as
    using different units), you might end up with issues.

### Yes

If the external class has the same attributes (name and type) as a given pysmo
type, then it should work out-of-the-box. You can verify this using
[`isinstance`][]:

<!-- skip: start -->

```python
>>> from pysmo import Location
>>> isinstance(my_external_object, Location)
True
>>>
```

<!-- skip: end -->

This is most likely to happen with simpler types like
[`Location`][pysmo.Location], which only requires `latitude` and `longitude`
attributes of type [`float`][].

### Yes, with a tiny bit of work

The most common reason a class doesn't match a pysmo type is that the
attribute names differ. For example, a class might store a station latitude in
an attribute called `stla` instead of `latitude`. In such cases, you can
create a thin subclass that maps the existing attributes to the expected names
using Python [properties](https://docs.python.org/3/library/functions.html#property):

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

This pattern is lightweight: the subclass inherits everything from the
original class and only adds the property aliases needed for pysmo
compatibility. Changing the aliased attributes also changes the originals and
vice versa. A concrete example of this pattern can be found in the
[`SAC`][pysmo.classes.SAC] API documentation.

### Yes, with a bit more work

Sometimes simple property aliases are not sufficient. This typically happens
when:

- **The same class needs to match the same type more than once.** For example,
  a class that stores both station and event coordinates cannot simply alias
  both to `latitude` and `longitude`, as the names would clash.
- **The data format differs.** The external class might store a time as a
  float (seconds since some reference), while pysmo expects a
  [`datetime`][datetime.datetime] object.
- **Some attributes are optional in the external class but required by the
  pysmo type.** You may need to add validation logic in the property getter.

In these cases, the recommended approach is to use **helper classes**. A helper
class is a small class that holds a reference to the parent object and provides
pysmo-compatible attribute access via properties:

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

Both `StationLocation` and `EventLocation` match the
[`Location`][pysmo.Location] type, while avoiding name clashes because each
helper class has its own namespace. Because they reference the parent object,
changes made through a helper class are reflected in the parent and vice versa.

With the helper classes in place, they can be added as attributes to a new
class that inherits from the external one:

<!-- skip: next -->

```python
class MyExtendedClass(ExternalClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.station_location = StationLocation(parent=self)
        self.event_location = EventLocation(parent=self)
```

## Examples

### `SAC`

The pysmo package itself uses this pattern for the
[`SAC`][pysmo.classes.SAC] class. The underlying
[`SacIO`][pysmo.lib.io.SacIO] class manages file I/O and provides access to
all SAC header fields using their original names (`stla`, `evla`, `b`, etc.).
These names do not match pysmo types, and several types (station location,
event location, seismogram data) coexist within a single object.

The [`SAC`][pysmo.classes.SAC] class solves this by inheriting from
[`SacIO`][pysmo.lib.io.SacIO] and adding helper-class attributes. While
[`SacIO`][pysmo.lib.io.SacIO] itself comprises roughly 800 lines of code,
the adaptation layer in [`SAC`][pysmo.classes.SAC] is only around 200.
Typically, it is much less work to adapt an existing class than what went into
building it in the first place:

```python
>>> from pysmo import Seismogram, Station, Event
>>> from pysmo.classes import SAC
>>> sac = SAC.from_file("example.sac")
>>> isinstance(sac.seismogram, Seismogram)
True
>>> isinstance(sac.station, Station)
True
>>> isinstance(sac.event, Event)
True
>>>
```

For more details, see the [`SAC`][pysmo.classes.SAC] API documentation.

### ObsPy's `Trace`

The [`SAC`][pysmo.classes.SAC] example above is pysmo's own code adapting
pysmo's own [`SacIO`][pysmo.lib.io.SacIO] class — useful to see the pattern
used for real, but not literally an external class. A more realistic case
for many seismologists: you already have waveform data as an
[ObsPy](https://docs.obspy.org/) `Trace` object and want to run pysmo's
functions and tools on it without converting your whole workflow.

`Trace.stats` stores `starttime` as ObsPy's own `UTCDateTime` type (not
[`pandas.Timestamp`][]) and `delta` as a plain `float` in seconds (not
[`pandas.Timedelta`][]), so this needs the "attribute name and format
differ" treatment from above, not the free out-of-the-box case: the adapter
needs properties that convert between the two, not simple aliases.
(`end_time` isn't read from `Trace.stats.endtime` at all — it's derived
from `begin_time` and `delta` instead, the same way
[`Seismogram`][pysmo.Seismogram]'s `end_time` is meant to be computed.)

`Trace` is also mutable, in both directions. ObsPy's own processing methods
(`.filter()`, `.taper()`, `.detrend()`, etc.) mutate it after you obtain it,
and [`pysmo.functions`][] mutates it too, the other way round: functions
like [`detrend`][pysmo.functions.detrend]/[`crop`][pysmo.functions.crop]/
[`resample`][pysmo.functions.resample] assign to `.data`/`.delta`/
`.begin_time` in place rather than returning a new object (unless called
with `clone=True`). So both directions need to work, which means this
adapter needs read/write properties with setters that write back to
`self._parent`, matching [`SacSeismogram`][pysmo.classes.SacSeismogram]'s
existing getter/setter pairs — not a read-only version.

```python title="trace_seismogram.py"
--8<-- "docs/snippets/external_classes/trace_seismogram.py"
```

<!-- skip: start -->

```python
>>> import numpy as np
>>> from obspy import Trace
>>> from pysmo import Seismogram
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
>>> isinstance(trace_seis, Seismogram)
True
>>> detrend(trace_seis)
>>> trace.data
array([...])
>>>
```

<!-- skip: end -->

With the setters in place, every [`pysmo.functions`][] and
[`pysmo.tools`][] call that takes a [`Seismogram`][pysmo.Seismogram] works
on `trace_seis` directly — including the ones that mutate in place, like
`detrend` above. Note what this adapter does *not* attempt: `Trace.stats`
has no latitude/longitude — that lives in ObsPy's separate `Inventory`
hierarchy, not on `Trace` itself — so `TraceSeismogram` only ever satisfies
[`Seismogram`][pysmo.Seismogram], never [`Station`][pysmo.Station]. Supply
station/event metadata separately, the same way
[`GeoCsvSeismogram.fetch()`][pysmo.classes.GeoCsvSeismogram.fetch] does.

!!! tip

    Notice `detrend` is available in two different shapes above: ObsPy
    exposes it as a method on `Trace` (`trace.detrend(...)`), while pysmo
    exposes the same operation as a standalone function that takes a
    [`Seismogram`][pysmo.Seismogram] (`detrend(seismogram)`). That
    difference isn't incidental. A method bound to `Trace` only ever works
    on a `Trace` (or a subclass of it). A function written against the
    [`Seismogram`][pysmo.Seismogram] protocol works on anything that
    satisfies it — `TraceSeismogram` here,
    [`SacSeismogram`][pysmo.classes.SacSeismogram], a
    [mini class](mini-classes.md), or any bespoke class you write yourself.
    That's why the exact same [`detrend`][pysmo.functions.detrend] call
    works unchanged on the [`SAC`][pysmo.classes.SAC] example above and on
    `trace_seis` here, with no dispatch logic anywhere to make that happen.
    Targeting the protocol rather than one specific class is what makes
    every function in [`pysmo.functions`][]/[`pysmo.tools`][] reusable this
    way. And it isn't limited to pysmo's own functions — any function you
    write yourself against [`Seismogram`][pysmo.Seismogram] gets the same
    property for free.

## Beyond adapting existing classes

Everything above is about making an external class usable with pysmo's
*existing* functions, in Python. That's useful, but it undersells what a
pysmo type actually is.

You've already built this twice in this chapter, in two different shapes,
without necessarily naming what it was. The helper-class approach builds a
narrow view as a separate object that reads from — and writes back to — a
richer parent; [`SacSeismogram`][pysmo.classes.SacSeismogram] is a real
example of exactly this: [`SAC`][pysmo.classes.SAC] carries the full
complexity of a SAC file's header, [`SacSeismogram`][pysmo.classes.SacSeismogram]
exposes only what [`Seismogram`][pysmo.Seismogram] needs. The thin-subclass
approach doesn't even need a separate object: a single bespoke class can
carry its own extra attributes directly, alongside the ones a protocol
requires, and still be handed to any function expecting that protocol
unchanged. Either way, the "rich" and "narrow" views aren't two objects with
data copied between them — they're two readings of the same one.

That's actually a general pattern, not something specific to these two
examples. The same object can be two different things at once, depending on
who's looking at it. To the code that owns it, a seismogram can carry
arbitrarily rich, problem-specific state — processing history, quality
flags, picks, provenance, whatever the task at hand actually needs. To a
function written against [`Seismogram`][pysmo.Seismogram], that same object
is just `begin_time`, `data`, `delta`, nothing more. Both are true at the
same time, of the same instance — the type doesn't strip anything away, it
just describes which part of the object a given piece of code has committed
to relying on.

The narrow view is the more interesting half of that pair. A type like
[`Seismogram`][pysmo.Seismogram] isn't really a Python feature — it's a
minimal specification of what a seismogram fundamentally needs to be,
arrived at by asking what processing functions actually require rather than
what any one class happens to expose (see
[What should become a type?](types.md#what-should-become-a-type)).
[`Protocol`][typing.Protocol] is simply the notation this specification
happens to be written in today. The definition itself — begin time, data,
sampling interval, nothing more — would translate just as directly into a
struct in C or Fortran, a database schema, or a paragraph of prose. It
doesn't depend on Python, or on pysmo, to remain true.

That distinction matters over a project's lifetime. Libraries and file
formats change — sometimes for good reasons, sometimes just because tooling
fashions shift — and code written directly against one specific class
inherits that churn. Code written against a well-considered, minimal
interface mostly doesn't: only the adaptation layer at the boundary needs to
change, not the logic behind it. The same holds on a smaller scale too —
say you move a slow step like [`mccc`][pysmo.tools.signal.mccc] from Python
to a compiled language for speed. The hard part of a move like that is
never translating syntax — it's figuring out what the actual minimal data
model needs to be. If that work is already done, captured as a small,
deliberate interface rather than smeared across whatever attributes a
particular class happened to expose, the move means reimplementing the
interface and its adapters in the new language's idiom, not re-deriving the
whole data model from scratch.

It isn't only external change that's unpredictable, either. You rarely know
in advance how complex the class supporting a particular problem will need
to become. A bespoke class doesn't have to mean a dataclass with a few extra
attributes — that's the simplest case, not the only one. What starts that
way can, as a project's real requirements surface, turn into something far
more involved. [AIMBAT](https://github.com/pysmo/aimbat) — an arrival-time
picking package built on pysmo — shows both ends of that range. Its first
version had nowhere else to put processing state, so it stored things like
filter parameters directly in SAC's generic
`user6`/`user7`/`kuser1`/`kuser2` header fields — fields with no defined
meaning of their own, repurposed because nothing better was available.
(It's also why old AIMBAT-processed SAC files can have oddly-populated
header fields that are confusing to decode later, if you ever come across
one.) Current AIMBAT solves the same problem properly instead: its
seismogram objects are backed by a SQL database, with `begin_time` and
`delta` stored as ordinary table columns and `data` fetched from a separate
table only when it's actually needed. That split pays off in a very
concrete way too: changing a pick or a sampling interval is a small
database update, not a read of the whole waveform file. Do the same thing
with a SAC file being read directly, and there's no such distinction
available — updating one value means touching the entire seismogram. None
of that is something you can plan for up front, and it doesn't need to be.
The protocol boundary doesn't ask the rich side to stay simple, or to stay
anything in particular — only that
[`begin_time`][pysmo.Seismogram.begin_time],
[`data`][pysmo.Seismogram.data], and
[`delta`][pysmo.Seismogram.delta] keep meaning what they always meant. The
processing logic on the other side of that boundary never has to change, no
matter how unrecognisable the rich side becomes.

Pysmo's types are one attempt at doing this work for seismology. The same
exercise is worth doing for whatever is specific to your own project.
