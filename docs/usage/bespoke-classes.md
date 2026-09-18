---
icon: lucide/wrench
tags:
  - Classes
  - Usage
---

# Writing a bespoke class

Most code needs to keep track of information as it moves between functions. That
information is state. A class holds it. Attributes are declared once, and an
instance carries them around as a single object, instead of a scattered handful
of separate variables.

A class's attributes should match the state a problem actually needs, named for
what they mean to it. General-purpose classes rarely fit that well. The
workarounds pile up, often several at once:

- Attributes the problem does not need get dragged along anyway, because the
    class is used wholesale. [`SAC`][pysmo.classes.SAC] carries close to a
    hundred header fields. Almost any piece of code only cares about a handful.
- Attributes the problem does need, but the class lacks, live on a second
    object instead. That object has to be kept in step with the first, for
    instance a `MiniSeismogram` alongside a dict of per-trace weights, indexed
    the same way. Window, sort, or drop an outlier from one, and the caller has
    to remember to do the same to the other, or the pairing quietly breaks.
- A generic or repurposed attribute stands in for a meaningful one. A `label`,
    or one of SAC's free-form `kuser0`/`kuser1`/`kuser2` headers, gets reused
    for whatever the problem needs this time. What it actually means is
    recorded in a comment, if anywhere.
- An attribute that does not always apply is made optional rather than left out,
    so code that cannot do anything useful without it has to check for `None`
    first anyway.

These are not alternatives. They often combine: a single class can carry
irrelevant fields, reuse one for the wrong purpose, and leave another optional,
all at once. A bespoke class untangles it. One object holds exactly the state
the problem needs, with attribute names that describe it, and every attribute
is always present (see
[types are always complete](./conventions.md#types-are-always-complete)). Modern
type hints make this checkable, not just a matter of discipline, as the next
section covers.

## Structure, not meaning

A class satisfies a pysmo type simply by matching its structure. Same names,
same types. Nothing confirms it also matches the meaning behind that
structure. An attribute of the right name and type is enough. It does not have
to actually hold what that name promises, computed correctly, in the right
units and convention.

In practice this rarely bites. Pysmo types mostly describe plain data, not
behaviour, so there is little logic to get wrong in the first place. On a
bespoke class the responsibility still sits with whoever wrote it. The same
person choosing the attribute names also decides what they hold.

!!! note "`runtime_checkable`"

    `typing.Protocol` classes can opt into `isinstance()` checks via
    `@runtime_checkable`, but it only confirms the named attributes exist, not that
    they hold the right types. It over-promises. Pysmo skips it for that reason, and
    because type checking belongs before runtime, not during it. A hand-written
    `TypeIs` guard is the more honest tool. See external classes for
    [when a runtime check is genuinely needed](./external-classes.md#when-a-runtime-check-is-genuinely-needed).

## A minimal bespoke `Seismogram`

Nothing in pysmo, or in any general-purpose seismogram class, has a `cheese`
attribute. Tapping a wheel of cheese and recording the resulting vibration
produces something structurally identical to a seismogram. A begin time, a
sampling interval, an array of samples. What the recording also needs is a
record of which wheel produced it, since the response depends on the cheese
itself. Writing the class directly, `cheese` included, is simpler than pairing a
general-purpose one with a second object to carry what it lacks:

<!-- skip: start -->

```python
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd


@dataclass
class Cheese:
    variety: str
    age: pd.Timedelta
    rind: str = "natural"


@dataclass
class CheeseSeismogram:
    begin_time: pd.Timestamp
    delta: pd.Timedelta
    data: npt.NDArray[np.floating]
    cheese: Cheese

    @property
    def end_time(self) -> pd.Timestamp:
        if len(self.data) == 0:
            return self.begin_time
        return self.begin_time + self.delta * (len(self.data) - 1)
```

<!-- skip: end -->

`cheese` is exactly the kind of project-specific attribute a general-purpose
type like [`Seismogram`][pysmo.Seismogram] never asks for and never sees. It
does not even have to be a simple one. `Cheese` is itself a small dataclass, and
`CheeseSeismogram.cheese` carries the whole thing without friction. Functions
annotated with `Seismogram` will not touch `cheese` at all, and
`CheeseSeismogram` still satisfies the type. The three attributes the protocol
cares about are stored fields with the right types. `end_time` is computed
from them. That is the whole contract, however elaborate the rest of the class
gets.

Reusability is only half of it. A function written specifically for this problem
can use `cheese` directly, and reads exactly like the domain it describes:

<!-- skip: start -->

```python
def ripeness(seismogram: CheeseSeismogram) -> pd.Timedelta:
    return seismogram.cheese.age
```

<!-- skip: end -->

Compare that to the same information stored on a class not built for the job. A
SAC file has no `cheese` header. The closest it offers is one of the free-form
`kuser0`/`kuser1`/`kuser2` fields, so a cheese's age ends up encoded as a
string, in whatever format whoever wrote it chose:

<!-- skip: start -->

```python
def ripeness(sac: SAC) -> str | None:
    return sac.native.kuser1
```

<!-- skip: end -->

Nothing about that second signature says `kuser1` holds a cheese's age, or in
what format. The type is wrong, the name is wrong, and finding out either means
tracking down whoever put it there. In another project, `kuser1` might hold a
vegetable's ripeness instead, or a QC flag, or nothing at all. The field itself
carries no memory of what it was ever used for.

Cheese is a deliberately silly example. A realistic one would make the same
point less obviously. No class meant for general use can anticipate what
attributes a project will need, mundane or exotic. A class built for the job
does not have that problem. Whoever writes it can just add whatever the
project turns out to need. The result is reusable wherever a `Seismogram` is
expected, and just as usable for exactly what it was built for. That is the
whole idea, cheese or not.

## Structural subtyping in practice

Structural subtyping cuts both ways. It makes a bespoke class quick to write.
It also makes one easy to write in a way that quietly breaks the functions
using it, with nothing flagging the mistake. What follows shows both sides,
in real pysmo code.

### Validation and conversion

`CheeseSeismogram` above stores whatever it is given, with no checks. A
string given where `begin_time` expects a timestamp draws no complaint at
assignment. The mistake surfaces later, wherever the code first tries to use
that string as a timestamp, far from where it was set.

Pysmo's own [Mini classes](./mini-classes.md) close that gap, building on the
`attrs` package instead of a plain `dataclass`. Each attribute is converted
(a `float`, a `str`, a `datetime`, turned into the correct `pd.Timestamp` or
`pd.Timedelta`) and validated (values of the right type but no physical
sense, a negative sampling interval say, get rejected). That is stricter than
a pysmo type itself demands. A pysmo type only checks that `begin_time`,
`delta` and `data` exist, with the right types, not that a negative `delta`
was ever refused. Detail in
[Forgiving on input, strict on values](./mini-classes.md#forgiving-on-input-strict-on-values).

A bespoke class gets the same checks for free by building on the matching
Mini class instead of a bare `dataclass`. `begin_time`, `delta` and `data`
arrive already converted and validated. Only `cheese` needs adding:

<!-- skip: start -->

```python
from attrs import define, field
from pysmo import MiniSeismogram


@define(kw_only=True)
class CheeseSeismogram(MiniSeismogram):
    cheese: Cheese = field()
```

<!-- skip: end -->

This works because `CheeseSeismogram` subclasses `MiniSeismogram`, inheriting
everything it already checks, plus `cheese`. Pysmo mostly avoids inheritance
in its own code. It prefers separate classes connected only by shared
attribute names. Subclassing couples two implementations more tightly than
that
([prefer functions over methods](./conventions.md#prefer-functions-over-methods)
has the reasoning). For a bespoke class, reusing a Mini class's checks this
way is a shortcut over rewriting them, not a licence to chain classes
together generally. This is structural subtyping's good side.
`CheeseSeismogram` enforces its own rules and carries its own state, and any
function written against `Seismogram` still takes it without complaint.

### What `replace` and `copy` assume

The other side shows up when generic code treats two differently-built
classes as interchangeable, just because both satisfy `Seismogram`. Pysmo's
own `replace=True` pattern and a plain `copy.deepcopy` both do this.
[`SacSeismogram`][pysmo.classes.SacSeismogram] is the concrete case. Its
`data` is a property that reads and writes straight through to the
underlying [`SacIO`][pysmo.lib.io.SacIO] instance's own stored field, rather
than holding a stored array of its own
([`SAC`](./external-classes.md#sac) has the full picture). `replace=True`
rebuilds its result by handing a freshly computed `data` to the class, the
same way construction would. That needs `data` to be an ordinary field. A
live view is not one. Calling a function with `replace=True` on a
`SacSeismogram` raises `TypeError` for exactly that reason (worked example in
[`pysmo.functions`][]). There is no field to hand the new array to.

`copy.deepcopy` runs into a related but different trap. Deep-copying a whole
[`SAC`][pysmo.classes.SAC] instance works correctly. Its
`__attrs_post_init__` rebuilds `seismogram`, `station` and `event` around one
new, copied `SacIO` instance, so they still agree with each other, exactly as
the originals did. Deep-copying just `sac.seismogram` on its own does not:

<!-- skip: start -->

```python
copied_seismogram = copy.deepcopy(sac.seismogram)
copied_station = copy.deepcopy(sac.station)
copied_seismogram._parent is copied_station._parent  # False
```

<!-- skip: end -->

Each call deep-copies the entire underlying `SacIO` header set on its own.
`copied_seismogram` and `copied_station` end up bound to two different,
disconnected clones, instead of the one shared parent `sac`'s own helpers
agree on. Setting a new station latitude on `copied_station` never shows up
through `copied_seismogram`, even though on `sac` itself the two are views of
the same object. Nothing raises here. The copy just silently stops being the
class the rest of the code assumes it is.

The lesson generalises beyond `SAC`. A class sharing state across several
attributes, or producing one of them on the fly instead of storing it, needs
generic operations like `replace=True` or `copy.deepcopy` to know about that,
to preserve it correctly. `SAC`'s own docstring spells out how it expects to
be copied or rebuilt. A bespoke class benefits from the same.

### The payoff

Both examples above are about internals a class author needs to get right.
The payoff is what makes that worthwhile. A bespoke class does not have to
settle on one way of holding its state. It only needs to produce the right
values, of the right type, the moment something asks for them.

Seismology's relationship with its own data is shifting the same way. What
was routinely a file on local disk is, increasingly, a row in a database, the
result of a live query against a web service, or a burst of samples arriving
over a socket, gone once read. A bespoke class is not obliged to make the
same choice throughout, or even one choice at all. One attribute can read
straight off disk. Another can be fetched over the network the first time
anything asks for it, then cached. Another can be computed from the rest.
Another might not be a value at all until something writes to it, only a
promise to fetch or compute one once asked. A function written against a
pysmo protocol never sees any of that. It only sees a class that, at the
moment it is asked, happens to hold exactly what was requested. Structural
subtyping makes mixing all of this inside one class possible. A protocol
asks only that the right names and types show up, never how they got there.
