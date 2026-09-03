---
icon: lucide/boxes
tags:
  - Classes
  - Mini
  - Usage
---

# Mini classes

Because pysmo is built around its types rather than one all-encompassing class,
it has no single built-in class that all its functions and modules expect. As
shown in the [tutorial](../first-steps/tutorial.md), the intended approach is a
tailor-made class for each use case. When a class with exactly the attributes of
a given type is needed, pysmo provides its "Mini" classes. These are minimal
implementations of their respective types, named accordingly (for example,
[`Seismogram`][pysmo.Seismogram] has [`MiniSeismogram`][pysmo.MiniSeismogram]).
They also serve as a lightweight scratch copy for processing, covered in the
example workflow below.

## Forgiving on input, strict on values

Mini classes are deliberately forgiving on input and strict on values. They use
**converters** to accept a range of input types, and **validators** to ensure
those data make sense for seismological processing.

For example, when setting a sampling interval
([`delta`][pysmo.MiniSeismogram.delta]), the input can be a `float` (seconds), a
`str` (e.g. "10ms"), or a standard Python `timedelta` object. The Mini class
converts these into a canonical [`pandas.Timedelta`][pandas.Timedelta]. It does,
however, reject a negative value, since a negative sampling interval is
physically impossible.

Similarly, the [`data`][pysmo.MiniSeismogram.data] attribute accepts lists or
tuples and converts them to a [`numpy.ndarray`][numpy.ndarray] automatically.

This "forgiving on input, strict on value" approach also applies when modifying
attributes after the object has been created.

## MiniSeismogram

The [`MiniSeismogram`][pysmo.MiniSeismogram] class shows what a Mini class looks
like:

<!-- skip: next -->

```python
--8<-- "src/pysmo/_types/seismogram.py:mini-seismogram"
```

At first glance it looks similar to the examples in the tutorial. A closer look
shows some differences:

- Instead of the built-in [`dataclasses.dataclass`][] it uses [attrs.define][].
    The two look and work similarly, but attrs allows the validation and
    conversion mentioned above.
- The [`begin_time`][pysmo.MiniSeismogram.begin_time] is automatically converted
    to a [`pandas.Timestamp`][pandas.Timestamp]. Timezone-aware values are
    converted to UTC; timezone-naive values are assumed to be UTC.
- Some attributes have default values, usually replaced in real use but
    convenient for quick tests.

## Example workflow

Mini classes can be instantiated directly, but it is often convenient to create
one already populated with data from another object. Pysmo provides two
functions for this:

- [`clone_to_mini`][pysmo.functions.clone_to_mini] creates a new Mini class
    instance by copying matching attributes from an existing object. Attributes
    present in the source but not in the Mini class are ignored, resulting in a
    lightweight copy of the original data.
- [`copy_from_mini`][pysmo.functions.copy_from_mini] does the reverse: it copies
    attributes from a Mini class instance back to a compatible target object.

Together these enable a workflow where data are cloned into a Mini class for
processing, then copied back to the original object. The example below loads
data from a SAC file into a `MiniSeismogram`, processes it, and copies it back:

<!-- skip: next -->

```python
--8<-- "docs/snippets/mini-example.py"
```

1. `sac.seismogram` could be processed directly; this example assumes processing
    is faster on a `MiniSeismogram`.
