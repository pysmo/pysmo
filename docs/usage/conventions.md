---
icon: lucide/ruler
tags:
  - Conventions
  - Units
  - Usage
---

# Conventions

## Trust your data

Type annotations form a contract between different parts of your code, not
between your code and the data it processes. Pysmo does not use annotations to
validate data. Instead, it assumes that data arriving at a function is correct
and in the expected format. The recommended approach is to validate once at the
point of ingestion and trust the data from there. This is straightforward at the
class level with e.g. [`attrs`][] (which pysmo uses throughout).

## SI units

Mismatched units are a common source of errors and tedious format conversions.
Pysmo assumes [SI](https://en.wikipedia.org/wiki/International_System_of_Units)
units throughout, even where other conventions are common in seismology. This is
also consistent with e.g. [`scipy.constants`][]. A notable example is
[`depth`][pysmo.LocationWithDepth.depth], which is in metres (positive downward
from the surface) — many seismological tools use kilometres instead.

## Time

Pysmo uses pandas datetime types throughout. They behave similarly to built-in
datetime objects but integrate better with numpy arrays. Points in time are
always [`pandas.Timestamp`][pandas.Timestamp] objects with
[`tzinfo`][pandas.Timestamp.tzinfo] set to
[UTC](https://en.wikipedia.org/wiki/Coordinated_Universal_Time). All times are
absolute — relative offsets from some reference point are avoided. Time
intervals such as the sampling interval are always
[`pandas.Timedelta`][pandas.Timedelta] objects.

Many seismological data formats and tools store absolute times without recording
a timezone, even though the values are effectively UTC. In keeping with "trust
your data" above, a naive timestamp arriving at a pysmo type is therefore
assumed to represent UTC and is converted accordingly — it is not rejected. This
conversion happens once, at the class level; functions that accept timestamps do
not repeat it.

## SciPy and NumPy parameters

Where [`scipy`][] or [`numpy`][] functions are used, pysmo follows their
parameter definitions and ranges rather than seismology conventions. For
example, [`scipy.signal.windows.tukey`][] defines `alpha` between `0` and `1`,
whereas taper functions in seismology typically use `0` to `0.5`. Pysmo uses the
SciPy definition. Default parameter values follow SciPy and NumPy as well, which
may produce different results from equivalent functions in other programs such
as [SAC](https://ds.iris.edu/files/sac-manual/).

## Types are always complete

Pysmo types are semantically complete — a [`Location`][pysmo.Location] without a
latitude or longitude is not a location at all. For this reason, optional
attributes (those that could be [`None`][]) are avoided unless strictly
necessary. Every attribute a type defines is always present and meaningful. This
is one of the advantages of pysmo's protocol-based approach over monolithic
classes: because each type represents exactly one concept, code that receives a
[`Location`][pysmo.Location] can use its attributes directly, without first
checking that they have a value.

## Prefer functions over methods

Functions are preferred over methods. Methods on a type create coupling between
the type and specific behaviour, which works against reusability. Pysmo types
therefore contain almost no methods.

This applies to dunder methods too. Pysmo types are data containers, and special
behaviour via dunder methods would be ambiguous. If
[`Seismogram`][pysmo.Seismogram] had a [`__len__`][object.__len__] method, it
would be unclear whether `len(seismogram)` returns the number of samples or
something else — whereas `len(seismogram.data)` is unambiguous.
