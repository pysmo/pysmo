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

Throughout pysmo, time values use NumPy's [`datetime64`][numpy.datetime64] and
[`timedelta64`][numpy.timedelta64] types. Points in time in Protocol classes
(e.g. [`Seismogram.begin_time`][pysmo.Seismogram.begin_time],
[`Event.time`][pysmo.Event.time]) are [`datetime64[us]`][numpy.datetime64]
values (microsecond precision) assumed to be in
[UTC](https://en.wikipedia.org/wiki/Coordinated_Universal_Time). Time intervals
(e.g. [`Seismogram.delta`][pysmo.Seismogram.delta]) use
[`timedelta64[us]`][numpy.timedelta64] (microsecond precision).

NumPy datetime64 and timedelta64 types provide efficient array operations and
seamless integration with NumPy-based scientific computing workflows. For
functions that return sequences of time values (e.g. multiple arrival times,
delays from cross-correlation), pysmo uses NumPy arrays of datetime64/timedelta64
for efficiency.

Helper functions in [`pysmo.tools.utils`][] are provided to convert between
Python datetime/timedelta and NumPy datetime64/timedelta64 types when needed for
interoperability with external libraries or legacy code.

## SciPy and NumPy parameters

In places where [`scipy`][] or [`numpy`][] functions are used, pysmo will adhere
to the original parameter definitions (and ranges). For example,
[`scipy.signal.windows.tukey`][] takes a parameter `alpha` which ranges from
`0` to `1` whereas similar "taper" functions in seismology often use an `alpha`
that lies between `0` and `0.5` (whereby `0.5` does the same thing as `1` in
the SciPy version).

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
