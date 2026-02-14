---
icon: lucide/boxes
tags:

- Classes
- Mini
- Usage

---

# Mini Classes

Because pysmo is built around its types rather than some all encompassing class,
it doesn't have a native class that can be used with the various functions and
modules that come as part of this package. As shown in the
[tutorial](../first-steps/tutorial.md), the idea is for you to use a tailor
made class for a particular use case. However, should you find yourself needing
a class that has exactly the same attributes as a particular type, then pysmo
has you covered with its "Mini" classes. These classes are minimal
implementations of their respective types and are named accordingly (e.g.
for the [`Seismogram`][pysmo.Seismogram] type there is a
[`MiniSeismogram`][pysmo.MiniSeismogram] class).

## MiniSeismogram

To show what such a Mini class looks like we can look at the code for the
[`MiniSeismogram`][pysmo.MiniSeismogram] class:

<!-- skip: next -->

```python
--8<-- "src/pysmo/_types/_seismogram.py:mini-seismogram"
```

At a first glance it looks similar to the examples in the
[tutorial](../first-steps/tutorial.md). However, upon closer inspection you
might notice some differences:

- Instead of using the built-in [`dataclasses.dataclass`][] it uses
  [attrs.define][]. They look and work similarly, but we get the option to do
  things like validating input (here we make sure the
  [`begin_time`][pysmo.MiniSeismogram.begin_time] has the expected
  [`tzinfo`][datetime.tzinfo]).
- The [`delta`][pysmo.MiniSeismogram.delta] attribute isn't a simple
  [`timedelta`][datetime.timedelta]. Instead it uses a custom
  [`PositiveTimedelta`][pysmo.typing.PositiveTimedelta] type which is more
  restrictive; after all, a negative sampling interval doesn't make any sense.
  In combination with the [`beartype`][beartype.beartype] decorator this
  ensures no invalid values are accepted at runtime.
- Some default values are provided. These will typically be replaced in real
  world usage, but do allow for some convenience while quickly testing things.

## Example workflow

Mini classes can be instantiated directly, but it might be convenient to create
an instance and populate it at the same time with data from another type. Pysmo
provides two functions for this:

- [`clone_to_mini`][pysmo.functions.clone_to_mini] creates a new Mini class
  instance by copying matching attributes from an existing object. Attributes
  present in the source but not in the Mini class are ignored, resulting in a
  lightweight copy of the original data.
- [`copy_from_mini`][pysmo.functions.copy_from_mini] does the reverse: it copies
  attributes from a Mini class instance back to a compatible target object.

Together, these two functions enable a workflow where data are cloned into a
Mini class for processing, and the results are then copied back to the original
object. Here we load data from a SAC file into a
[`MiniSeismogram`][pysmo.MiniSeismogram], do some processing, and then copy it
back:

<!-- skip: next -->

```python
--8<-- "docs/snippets/mini-example.py"
```

1. We could also process `sac.seismogram` directly. For this example we will
   therefore assume the processing completes significantly faster using a
   [`MiniSeismogram`][pysmo.MiniSeismogram]...
