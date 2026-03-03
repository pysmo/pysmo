---
icon: lucide/graduation-cap
tags:
  - First steps
---

# Tutorial

This tutorial uses a simplified ambient noise scenario as a vehicle for showing
how pysmo fits into real code — not as a guide to ambient noise processing
itself. Along the way it covers:

- Defining a custom seismogram class for a specific use case.
- Writing functions that operate on it.
- Using pysmo types to make those functions reusable.

## Custom seismogram class

Our scenario involves ambient noise data where we want to track whether
earthquake signals are present, but have no need for event information. A
dataclass fits this well:

```python title="noise_seismogram.py"
--8<-- "docs/snippets/tutorial/noise_seismogram.py"
```

1. [`dataclass`][dataclasses.dataclass] is a decorator that automatically
   generates special methods for the class, such as `__init__`, `__repr__`, and
   `__eq__`, based on the class attributes. This makes it easier to create
   classes that are primarily used to store data.
2. Instance attributes are defined simply by declaring them in the class body
   with type annotations. Note the use of [`pandas.Timestamp`][] here - it is
   used throughout pysmo as the standard type for time information.
3. Attributes can have default values too.
4. Care must be given if default values are mutable types (like lists or
   dictionaries). In such cases, you need to use `field(default_factory=...)` to
   ensure that each instance of the class gets its own separate copy of the
   mutable object.
5. We add a read-only property `end_time` that computes the end time of the
   seismogram based on the start time, number of samples, and sampling interval.
6. Finally, we add an attribute that lets us know if our seismogram contains
   earthquake signals or not.

A real project would have more attributes, but this is enough to demonstrate
the pattern. Creating an instance:

```bash
$ python -i noise_seismogram.py
>>> begin_time = Timestamp("2023-01-01", tz="UTC")
>>> data = np.random.randn(1000)  # Simulated noise data
>>> noise_seis = NoiseSeismogram(begin_time=begin_time, data=data)
>>>
```

!!! info "Key observations"
    - The [`dataclass`][dataclasses.dataclass] decorator generates `__init__`,
      `__repr__`, and `__eq__` automatically, keeping the class focused on what
      it stores.
    - Keeping methods out of the class and writing separate functions instead
      maintains a clear separation between data storage and processing.
    - All attributes are non-optional — no `bool | None`. Functions that use
      this class can assume all fields are present and skip defensive `None`
      checks.

## Functions that operate on the new class

Two functions handle the processing:

- `check_for_earthquakes()`: checks whether earthquake signals are present.
- `detrend()`: detrends the seismogram data.

A first version:

```python title="functions_v1.py" hl_lines="11"
--8<-- "docs/snippets/tutorial/functions_v1.py"
```

The type hints are correct and mypy confirms it:

```bash
$ python -m mypy functions_v1.py
Success: no issues found in 1 source file
```

With type checking in place, mypy can also identify unreachable code.
Running with `--warn-unreachable`:

```bash
$ python -m mypy --warn-unreachable functions_v1.py
functions_v1.py:11: error: Statement is unreachable  [unreachable]
Found 1 error in 1 file (checked 1 source file)
```

The `else` branch is unreachable because `contains_earthquake` is
non-optional — it can only be `True` or `False`. Removing it:

```python title="functions_v2.py" hl_lines="8 9"
--8<-- "docs/snippets/tutorial/functions_v2.py"
```

1. At this point we know that `seismogram.contains_earthquake` can only be
   `False`, so we don't need an `elif` check anymore.

Mypy is happy with this version too:

```bash
$ python -m mypy --warn-unreachable functions_v2.py
Success: no issues found in 1 source file
```

!!! info "Key observations"
    - Type hints on both the class and the functions let mypy verify their
      interaction statically.
    - Non-optional attributes remove the need for defensive [`None`][] checks
      in functions, which also gives mypy enough information to spot dead code.
    - Type checking catches errors before runtime. For validation at runtime,
      consider a library like [pydantic](https://docs.pydantic.dev).

## Reusing functions in other contexts

Comparing the two functions, only `check_for_earthquakes()` relies on
`contains_earthquake` — the one attribute specific to this project. The
remaining attributes form a common baseline, suggesting `detrend()` should
work with other seismogram classes too. To test this, consider a second
project that stores the season alongside seismogram data:

```python title="season_seismogram.py"
--8<-- "docs/snippets/tutorial/season_seismogram.py"
```

1. [`StrEnum`][enum.StrEnum] limits the values a string attribute can take.
2. Much like with `NoiseSeismogram`, we have just one project-specific
   attribute (`season`).

??? tip "Mixin classes"
    In our two example classes, we write the `end_time` property in exactly the
    same way for both classes. If we had a lot of classes that needed to have
    the same implementation, we would be constantly repeating ourselves. To
    avoid this, we could write a *mixin* class that can be included in our
    class definitions:

    <!-- skip: next -->
    ```python
    --8<-- "src/pysmo/_types/seismogram.py:seismogram-mixin"
    ```

    This tiny class can be inherited by both `NoiseSeismogram` and
    `SeasonSeismogram`, and we can skip writing the `end_time` property:
    <!-- skip: next -->
    ```python title="season_seismogram_short.py"
    --8<-- "docs/snippets/tutorial/season_seismogram_short.py"
    ```

    1. `end_time` is inherited from `SeismogramEndtimeMixin`, so we don't need
      to write a implementation anymore.

    Note that there are complications that come along with class inheritance,
    so it is best to keep your mixin classes simple, or even focused on a single
    task (you can always add multiple mixins to your class if you need to).

Next we write a script that uses this new class together with the `detrend()`
function from earlier:

```python title="season_detrend_v1.py"
--8<-- "docs/snippets/tutorial/season_detrend_v1.py"
```

This script runs correctly:

```bash
$ python season_detrend_v1.py && echo "success\!"
success!
```

But mypy flags a type mismatch — `detrend()` expects a `NoiseSeismogram` and
is being passed a `SeasonSeismogram`:

```bash
$ python -m mypy season_detrend_v1.py
season_detrend_v1.py:16: error: Argument 1 to "detrend" has incompatible type "SeasonSeismogram"; expected "NoiseSeismogram"  [arg-type]
```

Type annotations prevent using non-existent attributes, but they don't
require using *all* of them. `detrend()` only touches `data`, which both
classes happen to share. We just got lucky this time.

To fix this, we need to amend the type annotations of the `detrend()` function:

```python title="functions_v3.py" hl_lines="2 13"
--8<-- "docs/snippets/tutorial/functions_v3.py"
```

1. We need to import `SeasonSeismogram` to be able to use it in our type
   annotations.

With these changes in place, mypy is happy again:

```bash
$ python -m mypy season_detrend_v2.py
Success: no issues found in 1 source file
```

!!! info "Key observations"
    - We have successfully reused the `detrend()` function in a different
      context.
    - However, it did require changing the type annotations of the function.
    - While the changes were small, making them every time we want to reuse the
      function is cumbersome.
    - The `check_for_earthquakes()` function is not reusable at all, as it
      relies on the `contains_earthquake` attribute that only exists in
      `NoiseSeismogram`. Thus we can identify two types of functions: those
      that are reusable and those that are not. This is also reflected in their
      respective type annotations.

## Introducing pysmo

Writing custom classes for each project and updating shared functions every
time a new class is introduced is difficult to maintain. Each new class
requires touching function annotations, and changes to any class risk breaking
the functions that depend on it. The standard solution is to define an
*interface* between functions and classes: functions target the interface, and
classes conform to it.

Pysmo provides such an interface for seismogram (and other) classes. These
interfaces make use of Python's [`Protocol`][typing.Protocol] class. Below is
the actual implementation of pysmo's [`Seismogram`][pysmo.Seismogram] interface:

```python
--8<-- "src/pysmo/_types/seismogram.py:seismogram-protocol"
```

Strip away the docstrings and this looks much like the common structure of
`NoiseSeismogram` and `SeasonSeismogram`. The key difference is that `end_time`
is declared but not implemented — [`Protocol`][typing.Protocol] classes provide
type information only and cannot be instantiated directly.

!!! note
    Python [`Protocol`][typing.Protocol] classes are used almost exclusively in
    type annotations. We will therefore refer to the ones shipped with pysmo as
    *types* rather than protocols or interfaces.

Python considers classes that have the same structure as a protocol class to be
subclasses of the protocol class. For our particular case, this means that
instances of `NoiseSeismogram` and `SeasonSeismogram` are also instances of
`Seismogram`.

Annotating `detrend()` with the `Seismogram` type rather than listing every
class:

```python title="functions_v4.py" hl_lines="2 13"
--8<-- "docs/snippets/tutorial/functions_v4.py"
```

1. Instead of importing `SeasonSeismogram`, we now import `Seismogram`.
2. Any class that satisfies the `Seismogram` structure is now accepted —
   no further changes to `detrend()` needed.

!!! info "Key observations"
    - The `detrend()` function now uses pysmo types in its annotations.
    - Because `NoiseSeismogram` and `SeasonSeismogram` are subclasses of
      `Seismogram`, type checkers will accept instances of `NoiseSeismogram`
      and `SeasonSeismogram` as valid inputs for `detrend()`.
    - Future custom seismogram classes will also be accepted as inputs without
      any changes to the `detrend()` function, provided the structure
      prescribed by the `Seismogram` type is adhered to.
    - The `check_for_earthquakes()` is still annotated with `NoiseSeismogram`,
      because it uses the `contains_earthquake` attribute that doesn't exist in
      the `Seismogram` type.

## Conclusion

This tutorial introduced the core ideas behind pysmo rather than its API:

- Pysmo is *not* centred around a single seismogram class. Monolithic classes
  tend to reflect the use cases their authors had in mind, not the ones users
  actually have.
- Custom seismogram classes fit specific use cases well, but create friction
  when writing reusable code.
- Pysmo addresses this by defining interfaces — *pysmo types* — that capture
  what different classes have in common. Functions target the interface; any
  conforming class works.
- Pysmo types are intentionally narrow: few attributes, almost no methods.

The same principles apply to the processing modules pysmo ships with, which
is why they work just as well in your own code as in pysmo's.
