---
icon: lucide/type
tags:
  - Types
  - Usage
---
# Types

If you are using pysmo, you are hopefully sold on the idea of using pysmo types
in your code. This section provides some background on how these types came to
be, and what to consider if you want to write some types of your own.

## Use patterns

Defining arbitrarily complex types using [`Protocol`][typing.Protocol] classes
is straightforward, and you may be (or perhaps should be!) tempted to use them
everywhere. However, precisely because it is so easy to write types, you may
want to take a moment to contemplate what exactly should go into the type you
are defining. For this it may be worth looking at different use patterns that
exist for custom types.

!!! note

    For simplicity, we will assume classes only contain attributes in the
    examples shown here. In a real-world situation, classes (and types) may of
    course contain methods too.

### Direct access

We begin by discussing the simplest case: no custom types at all. Consider a
class `SomeClass` that has attribute names corresponding to all letters of the
alphabet, i.e. `a`, `b`, `c`, ..., `z`. These data can be used in functions by
passing either the entire class to a function (`f1`), a subset of attributes
(`f2`), or all the individual attributes (`f3`):

```mermaid
flowchart TD
    C1@{ shape: das, label: "**SomeClass**
      a, b, c, ..., z" }
    C1 ---> F1@{ shape: rounded, label: "*f1*(SomeClass)" }
    C1 ---> F2@{ shape: rounded, label: "*f2*(Ta,Tb)" }
    C1 ---> F3@{ shape: rounded, label: "*f3*(Ta,Tb,Tc, ..., Tz)" }
```

Note that in the above diagram, we hint at the types of function arguments
rather than the names. The intention is to show that `f2`, for example, is
meant to be used with attributes `a` and `b` and should therefore be annotated
with the respective types of those attributes. Corresponding (pseudo) code
would look something like:

<!-- skip: next -->

```python
@dataclass
class SomeClass:
  a: float #(1)!
  b: float #(2)!
  c: str
  ...
  z: datetime

def f1(some_class: SomeClass):
  ...

def f2(a: float, b: float):
  ...

def f3(a: float, b: float, c: str, ..., z: datetime):
  ...

```

1. We are now being explicit about the type of `a`, so in the diagram above Ta
   is actually [`float`][].
2. Same for Tb and all other attributes.

Though the function bodies are not shown, we can safely assume that if they are
half-decently written, they use all declared function parameters. Thus `f2`
uses only a fraction of the attributes, while `f3` uses all attributes declared in
`SomeClass`. `f2` seems like a reasonable function then; it is simple, it is
clear what data are processed in the function body, and it is decoupled from
`SomeClass` because the attributes are used directly as function parameters.
`f3` is technically also decoupled. However, as all 26 attributes are passed
to the function, there appears to still be a strong link between the two.
Moreover, needing to provide 26 parameters every time `f3` is called seems
unreasonable; it makes more sense to write it like `f1` and pass it an instance
of `SomeClass` directly. As for `f1`, whether or not it is a reasonable
function depends on how many attributes are actually used. If it is a
significant enough amount it makes sense to write the function the way it is.
If only e.g. 2 attributes are used, we might want to write a function that
looks more like `f2`.

### Exact match

As writing types is rather easy, it is worth considering *always* using them.
Doing so immediately makes code more reusable and often more maintainable too.
We can use `SomeClass` as blueprint for the `TSomeClass` type, which is then
used to annotate `f1`. After doing so, we can start using `f1` with the
`SomeOtherClass` class that has the same attributes as `SomeClass`:

```mermaid
flowchart TD
    C1@{ shape: das, label: "**SomeClass**
      a, b, c, ..., z" }
    C2@{ shape: das, label: "**SomeOtherClass**
      a, b, c, ..., z, A, B, C, ..., Z" }
    T1@{ shape: stadium, label: "**TSomeClass**
      Ta, Tb, Tc, ..., Tz" }
    C1 ---> T1
    C2 ---> T1
    T1 e1@--- F1@{ shape: rounded, label: "*f1*(TSomeClass)" }
    e1@{ animate: true }
```

Here, `TSomeClass` is not meant to be a "pysmo-like" type. Not much thought
went into it other than "you never know if you'll use this some other
way one day". But you just might...

### Subset match

Pysmo types are often intended to group related data together. If we find
ourselves writing a lot of functions that use `a` and `b` as input, it is
likely there is a strong connection between those two attributes. They could
be something like the latitude and longitude of an event or station. We can
formally declare this relationship using a new type `T1` and use that in the
`f2` function instead of `a` and `b`. Similarly we define the `T2` type here
and use it for `f4`:

```mermaid
flowchart TD
    C1@{ shape: das, label: "**SomeClass**
      a, b, c, ..., z" }
    C2@{ shape: das, label: "**SomeOtherClass**
      a, b, c, ..., z, A, B, C, ..., Z" }
    T1@{ shape: stadium, label: "**T1**
      Ta, Tb" }
    T2@{ shape: stadium, label: "**T2**
      TA, TB" }
    C1 ---> T1
    C2 ---> T1
    C2 ---> T2
    T1 e1@--- F2@{ shape: rounded, label: "*f2*(T1)" }
    T2 e2@--- F4@{ shape: rounded, label: "*f4*(T2)" }
    e1@{ animate: true }
    e2@{ animate: true }
```

With these types we can seamlessly use `f2` with `SomeClass` as well as
`SomeOtherClass`, while `f4` works with `SomeOtherClass`. Using `T1` and `T2`
as input types for two parameters in yet another function `f5` looks like this:

```mermaid
flowchart TD
    C2@{ shape: das, label: "**SomeOtherClass**
      a, b, c, ..., z, A, B, C, ..., Z" }
    T1@{ shape: stadium, label: "**T1**
      Ta, Tb" }
    T2@{ shape: stadium, label: "**T2**
      TA, TB" }
    C2 ---> T1
    C2 ---> T2
    T1 e1@--- F5@{ shape: rounded, label: "*f5*(T1, T2)" }
    T2 e2@--- F5
    e1@{ animate: true }
    e2@{ animate: true }
```

A slightly odd consequence of using these types is that even though an instance
of `SomeOtherClass` contains all the data needed for `f5`, it has to be passed
to the function twice (once as `T1` and once as `T2`). Thus you might see
something like this appear in your code:

<!-- skip: next -->

```python
some_other_class = SomeOtherClass()
f5(some_other_class, some_other_class)
```

However, this slight drawback is easily offset by the increased flexibility we
gain from using custom types. For example, it is conceivable that `f5` was
originally written for `SomeOtherClass` instances, but now we suddenly find
ourselves in a situation where the data are spread across two different sources
`SomeClass` and `YetOtherClass`(1). Fortunately this isn't an issue thanks to
how types work:
{ .annotate }

1. :bulb: Perhaps you are mixing data sources like files, database queries, web
   requests, etc.

```mermaid
flowchart TD
    C1@{ shape: das, label: "**SomeClass**
      a, b, c, ..., z" }
    C3@{ shape: das, label: "**YetOtherClass**
      A, B, C, ..., Z" }
    T1@{ shape: stadium, label: "**T1**
      Tp, Ty" }
    T2@{ shape: stadium, label: "**T2**
      TP, TY" }
    C1 ---> T1
    C3 ---> T2
    T1 e1@--- F5@{ shape: rounded, label: "*f5*(T1, T2)" }
    T2 e2@--- F5
    e1@{ animate: true }
    e2@{ animate: true }
```

## What should become a type?

Discussing the different patterns above provides insight into some of the
practical aspects of types. However, there are some more fundamental things to
consider when defining types for pysmo. Essentially the idea is to take complex
data, and divide them into sensible, smaller pieces (whereby these pieces become
the basis for pysmo types). The single most important thing to keep in mind
while doing so, is that once defined these types should *never* change.

A useful strategy to follow is to determine precisely what data functions
actually need *before* specifying the types (arguably this is how
[`Protocol`][typing.Protocol] is meant to be used in the first place). When
doing so, the functions themselves should be written as general as possible.
For example, a common task is to calculate the distance between an event and a
station. However, that problem can be described more generally as calculating
the distance between two geographic locations. That is exactly why pysmo has
the [`Location`][pysmo.Location] type, which looks like this:

<!-- skip: next -->

```python
--8<-- "src/pysmo/_types/location.py:location-protocol"
```

Because these types are meant to be very stable, we can do something that is
often considered bad practice: class inheritance. In pysmo the
[`Location`][pysmo.Location] type is reused in the [`Station`][pysmo.Station]
type via inheritance:

<!-- skip: next -->

```python
--8<-- "src/pysmo/_types/station.py:station-protocol"
```

The result of this is that the [`Station`][pysmo.Station] type gets the
[`latitude`][pysmo.Location.latitude] and
[`longitude`][pysmo.Location.longitude]
attributes from [`Location`][pysmo.Location]. This means
[`Station`][pysmo.Station] classes can be used as input in functions annotated
with [`Location`][pysmo.Location].

In summary, the strategy for determining types can be summarised as follows:

1. Keep types as simple as possible.
2. Reuse simple types whenever possible in more complex types.

!!! tip

    If you ever find yourself contemplating a type with attribute names like
    `station_latitude` or `station_longitude`, you are likely defining a type
    that is too specific.

## Why does this type exist?

Not every pysmo type came into being for the same reason. It is worth being
able to tell the difference, because it changes what you should expect from
the type. Looking at existing pysmo types, three distinct origins emerge.

The first is a **convergence type**: [`Seismogram`][pysmo.Seismogram] is the
clearest example, and is discussed at length in the
["The pysmo solution"](motivation.md#the-pysmo-solution) section of the
[motivation](motivation.md) page. Here, the problem is that the real world
already has too many competing representations of the same concept — every
tool has its own waveform class. The type's entire purpose is to capture
what these representations have in common, so pysmo can operate on any of
them without privileging one or forcing a conversion. Third-party code is
expected to implement types like this directly; that is the "bring your own
class" idea pysmo is built around.

The second is a **converged-concept type**: [`Response`][pysmo.Response] and
its related types ([`ResponseStage`][pysmo.ResponseStage],
[`StagedResponse`][pysmo.StagedResponse]). Here the origin is different.
There is no proliferation of competing in-memory response designs to
reconcile — poles, zeros, and sensitivity are already the standard,
settled way this domain represents an analog instrument response. The type
names an already-agreed mathematical object rather than resolving external
disagreement. In practice, hardly anyone hand-implements a new
`Response`-conformant class from scratch the way they might for
[`Seismogram`][pysmo.Seismogram]; responses come from a small, closed set of
known sources (SAC PZ, StationXML, RESP), and pysmo already ships readers
for those. This type is still physically meaningful in the same way
[`Seismogram`][pysmo.Seismogram] is, just extended differently in practice.

The third is an **internal-refactor type**: it exists purely to let a pysmo
function type-check, not because anything outside pysmo needed naming.
`_EpochProvenance` (`src/pysmo/_types/response.py`) is the current example:
both [`SacPZ`][pysmo.classes.SacPZ] and [`StationXML`][pysmo.classes.StationXML]
carry the same six fields — network, station, location, and channel code,
plus a start and (optional) end date for the response epoch — because
[`write_sacpz`][pysmo.lib.io.write_sacpz] needed a name for that overlap to
type-check its input. Nobody has a competing `_EpochProvenance` design in
the wild; this is about avoiding duplication in pysmo's own code, not a
response to anything external.

The [`Location`][pysmo.Location]-in-[`Station`][pysmo.Station] inheritance
described above is the same "reuse simple types" instinct, applied one step
earlier: instead of factoring out duplication after the fact,
[`Location`][pysmo.Location] was identified as reusable from the start.

### Mini classes and root export are separate questions

It is tempting to assume that an internal-refactor type, being the least
"important" of the three, should also be the one that never gets a
[Mini class](mini-classes.md) or never appears in the `pysmo` root
namespace. Neither follows. Both are separate, need-based questions that
happen to correlate with origin without being defined by it.

A `Mini*` class exists only when some real code path needs to construct a
bare instance of exactly that type's fields on its own. `_EpochProvenance`
has no `MiniEpochProvenance` because nothing does: every real caller
already has a [`SacPZ`][pysmo.classes.SacPZ] or
[`StationXML`][pysmo.classes.StationXML] object carrying those six fields as
part of something bigger. That is a fact about how the type is actually
used, not a consequence of it being an internal-refactor type — a future
internal-refactor type whose callers *do* need a bare, standalone instance
would get a `Mini*` class the same as any other.

The same applies to membership of the internal `_BaseProto`/`_BaseMini`
type-alias unions (`src/pysmo/__init__.py`), which exist to make pysmo's
generic Mini-conversion machinery
([`proto2mini`][pysmo.lib.mini_utils.proto2mini],
[`matching_pysmo_types`][pysmo.lib.mini_utils.matching_pysmo_types],
[`clone_to_mini`][pysmo.functions.clone_to_mini],
[`copy_from_mini`][pysmo.functions.copy_from_mini]) work. A type is only
useful to that machinery if a `Mini*` counterpart exists to convert to or
from, so `_EpochProvenance` — having no `Mini*` class — has no reason to be
in `_BaseProto` either. This is not a separate judgement call about
importance; it follows mechanically from the same need-based rule.

Whether a type is exported at the `pysmo` root namespace (importable as
`from pysmo import X`, and therefore listed on the
[API reference](../api/pysmo.md)) is a third, again independent, question.
An internal-refactor type usually shouldn't be: `_EpochProvenance` is
private for exactly this reason, following the precedent set by other
internal-only types such as `SeismogramEndtimeMixin`. Code that needs to
reference the composed result from outside `src/pysmo/_types/response.py`
uses [`ResponseWithEpoch`][pysmo.lib.io.ResponseWithEpoch] instead — the
actual public type built from it.

One more pattern is worth flagging before moving on, because it sits next
to these three without being a fourth origin:
[`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram], covered in the next
section, *extends* [`Seismogram`][pysmo.Seismogram] with extra fields for
one algorithm's bookkeeping. It is internally motivated in the same way an
internal-refactor type is, but shaped the opposite way — adding fields for
one tool's needs rather than factoring out fields shared by several
concrete classes. It is not a fourth origin, just a tool-scoped extension
of an existing one.

## Specialised types

The basic types included in pysmo may become insufficient for the more complex
scenarios in the [`pysmo.tools`][] modules. Insisting on only using the basic
[`Seismogram`][pysmo.Seismogram] type would require writing functions with lots
of additional input parameters, therefore becoming tedious to write and use.

This is why some of the components in the pysmo package (e.g.
[`pysmo.tools.iccs`][pysmo.tools.iccs]) use their own types
([`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram]) rather than the basic
pysmo types. Crucially, these types inherit from the basic pysmo types, and
therefore can still be used the same way as e.g. a basic
[`Seismogram`][pysmo.Seismogram].

!!! tip

    These specialised types all have a corresponding
    [mini class](mini-classes.md).
    Thus, if you are working with a class that matches e.g. the
    [`Seismogram`][pysmo.Seismogram] type, but not the
    [`IccsSeismogram`][pysmo.tools.iccs.IccsSeismogram] type, you can create a
    [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram] object using
    the [`clone_to_mini()`][pysmo.functions.clone_to_mini] function by adding
    the missing attributes via the `update` argument.
