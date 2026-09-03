---
icon: lucide/ruler
tags:
  - Conventions
  - Units
  - Usage
---

# Conventions

## Trust your data

Type annotations form a contract between different parts of a program, not
between the code and the data it processes. Pysmo does not use annotations to
validate data. Instead, it assumes the data arriving at a function are correct
and in the expected format. Validate once, at the point of ingestion, and trust
the data afterwards. At the class level this is straightforward with a library
such as [`attrs`][], which pysmo uses throughout.

## SI units

Mismatched units are a common source of errors and tedious format conversions.
Pysmo assumes [SI](https://en.wikipedia.org/wiki/International_System_of_Units)
units throughout, even where other conventions are common in seismology. This is
also consistent with [`scipy.constants`][], for example. A notable case is
[`depth`][pysmo.LocationWithDepth.depth], which is in metres, positive
downwards, where many seismological tools use kilometres instead.

## Time

Pysmo uses pandas datetime types throughout rather than the built-in
[`datetime`][datetime.datetime] module. Unlike `datetime`, pandas timestamps and
time intervals are backed by the same array machinery as [`numpy`][]. An
operation across many values at once (shifting every pick time in an array by a
fixed offset, say) then runs as a single array operation rather than a Python
loop over individual objects, and is correspondingly faster.
[`pysmo.tools.noise.NoiseModel`][] stores its period axis this way, as a
[`pandas.TimedeltaIndex`][] built in one call to [`pandas.to_timedelta`][]
rather than one [`pandas.Timedelta`][] at a time.

Points in time are always [`pandas.Timestamp`][] objects with
[`tzinfo`][pandas.Timestamp.tzinfo] set to
[UTC](https://en.wikipedia.org/wiki/Coordinated_Universal_Time). All times are
absolute; relative offsets from some reference point are avoided. Time intervals
such as the sampling interval are always `pandas.Timedelta` objects, not bare
floats: a float has no fixed unit attached (seconds? samples? days?), and
converting between units or across calendar boundaries by hand (leap years,
variable month lengths, leap seconds) is a common source of bugs.
`pandas.Timestamp` and `pandas.Timedelta` handle that arithmetic internally,
storing values as integer nanoseconds and avoiding the rounding error that
floating-point seconds accumulate under repeated arithmetic.

Many seismological data formats and tools store absolute times without recording
a timezone, even though the values are effectively UTC. In keeping with "trust
your data" above, a naive timestamp arriving at a pysmo type is therefore
assumed to represent UTC and is converted accordingly, not rejected. This
conversion happens once, at the class level; functions that accept timestamps do
not repeat it.

## SciPy and NumPy parameters

Where [`scipy`][] or `numpy` functions are used, pysmo follows their parameter
definitions and ranges rather than seismology conventions. For example,
[`scipy.signal.windows.tukey`][] defines `alpha` between `0` and `1`, whereas
taper functions in seismology typically use `0` to `0.5`. Pysmo uses the SciPy
definition. Default parameter values follow SciPy and NumPy as well, which may
produce different results from equivalent functions in other programs such as
[SAC](https://ds.iris.edu/files/sac-manual/).

## Types are always complete

Pysmo types are semantically complete: a [`Location`][pysmo.Location] without a
latitude or longitude is not a location at all. For this reason, optional
attributes (those that could be [`None`][]) are avoided unless strictly
necessary. Every attribute a type defines is always present and meaningful. This
is one of the advantages of pysmo's protocol-based approach over monolithic
classes: because each type represents exactly one concept, code that receives a
`Location` can use its attributes directly, without first checking that they
have a value.

## Prefer functions over methods

Functions are preferred over methods. Methods on a type create coupling between
the type and specific behaviour, which works against reusability. Pysmo types
therefore contain almost no methods.

The same applies to Python's special methods, those with double-underscore names
such as `__len__`. Pysmo types are data containers, and giving them special
behaviour this way would be ambiguous. If [`Seismogram`][pysmo.Seismogram] had a
[`__len__`][object.__len__] method, `len(seismogram)` could mean the number of
samples or something else. `len(seismogram.data)` is unambiguous.
