---
icon: lucide/ruler
tags:
  - Conventions
  - Units
  - Usage
---

# Conventions

## SI units

All too often mismatched units are to blame for outright errors, or at least
tedious extra work to get data into the correct format. Therefore, even if it
goes against common usage patterns, units are assumed to be
[SI](https://en.wikipedia.org/wiki/International_System_of_Units) everywhere.
This is also consistent with e.g. [`scipy.constants`][].

## Time

Throughout pysmo you will notice extensive use of pandas datetime types.
Pandas time objects are used similarly to built-in datetime objects, but work
better with numpy arrays. Points in time are always [`pandas.Timestamp`][pandas.Timestamp]
objects with the [`tzinfo`][pandas.Timestamp.tzinfo] attribute set (ideally to
[UTC](https://en.wikipedia.org/wiki/Coordinated_Universal_Time)). Time
calculations are straightforward with pandas datetime types, so things like
relative times (e.g. for a begin time in a seismogram) are avoided. Similarly,
time deltas (e.g. sampling interval) are always [`pandas.Timedelta`][pandas.Timedelta]
objects.

## SciPy and NumPy parameters

In places where [`scipy`][] or [`numpy`][] functions are used, pysmo will adhere
to the original parameter definitions (and ranges). For example,
[`scipy.signal.windows.tukey`][] takes a parameter `alpha` which ranges from
`0` to `1` whereas similar "taper" functions in seismology often use an `alpha`
that lies between `0` and `0.5` (whereby `0.5` does the same thing as `1` in
the SciPy version).

Default values of parameters are treated the same way (i.e. pysmo sticks to the
SciPy and NumPy defaults), so differences between results from calling a pysmo
function and the equivalent function in another library or program (e.g.
[SAC](https://ds.iris.edu/files/sac-manual/)) may be possible.

## Avoid None type

Pysmo types are meant to be specific and narrowly defined. Unless absolutely
necessary, using the [`None`][] type is avoided. Consider for example a
`Coordinates` type that has a `latitude` and a `longitude` attribute. As
coordinates *always* have a latitude and a longitude, it should not be possible
to set either of those attributes to [`None`][].

## Prefer functions over methods

It is generally better to use functions than methods, or at the very least the
number of methods should be kept at a minimum. This is even more so when code
re-usability becomes a factor. Hence pysmo types almost never contain methods.

This extends to magic (dunder) methods as well. Pysmo types are intended to be
data containers, so adding special behaviour via dunder methods would be
surprising and potentially confusing. For example, if
[`Seismogram`][pysmo.Seismogram] had a [`__len__`][object.__len__] method, it
would be unclear whether `len(seismogram)` returns the number of samples or
something else entirely — whereas `len(seismogram.data)` is unambiguous.
