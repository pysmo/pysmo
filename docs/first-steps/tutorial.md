---
icon: lucide/graduation-cap
tags:
  - First steps
---

# Tutorial

This tutorial uses a simplified ambient noise scenario to show how pysmo fits
into real code. It is not a guide to ambient noise processing. Along the way it
covers:

- Defining a custom seismogram class for a specific use case.
- Writing functions that operate on it.
- Using pysmo types to make those functions reusable.

## Custom seismogram class

The scenario involves ambient noise data. It needs to track whether earthquake
signals are present, but has no need for event information. A dataclass fits
this well:

```python title="noise_seismogram.py"
--8<-- "docs/snippets/tutorial/noise_seismogram.py"
```

1. [`dataclass`][dataclasses.dataclass] is a decorator that generates the
    methods a data-holding class normally needs, based on the attributes
    declared in the class body: one to create instances, one to show them as
    readable text, one to compare them for equality. It saves writing them by
    hand.
2. Instance attributes are defined simply by declaring them in the class body
    with type annotations. Note the use of [`pandas.Timestamp`][] here. It is
    used throughout pysmo as the standard type for time information.
3. Attributes can have default values too.
4. Mutable default values (like lists or dictionaries) need
    `field(default_factory=...)`, so that each instance gets its own separate
    copy.
5. A read-only `end_time` property computes the end time from the start time,
    number of samples, and sampling interval.
6. Finally, an attribute records whether the seismogram contains earthquake
    signals.

A real project would have more attributes, but this is enough to demonstrate the
pattern. Creating an instance:

```bash
$ uv run python -i noise_seismogram.py
>>> begin_time = Timestamp("2023-01-01", tz="UTC")
>>> data = np.random.randn(1000)  # Simulated noise data
>>> noise_seis = NoiseSeismogram(begin_time=begin_time, data=data)
>>>
```

!!! info "Key observations"

    - The `dataclass` decorator writes the instance-creation, text-representation,
        and equality code automatically, keeping the class focused on what it
        stores.
    - Keeping methods out of the class and writing separate functions instead
        maintains a clear separation between data storage and processing.
    - All attributes are non-optional: no `bool | None`. Functions that use this
        class can assume all fields are present and skip defensive [`None`][]
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
$ uv run mypy functions_v1.py
Success: no issues found in 1 source file
```

With type checking in place, mypy can also identify unreachable code. Running
with `--warn-unreachable`:

```bash
$ uv run mypy --warn-unreachable functions_v1.py
functions_v1.py:11: error: Statement is unreachable  [unreachable]
Found 1 error in 1 file (checked 1 source file)
```

The `else` branch is unreachable because `contains_earthquake` is non-optional:
it can only be `True` or `False`. Removing it:

```python title="functions_v2.py" hl_lines="8 9"
--8<-- "docs/snippets/tutorial/functions_v2.py"
```

1. At this point `seismogram.contains_earthquake` can only be `False`, so the
    `elif` check is no longer needed.

Mypy reports no errors here either:

```bash
$ uv run mypy --warn-unreachable functions_v2.py
Success: no issues found in 1 source file
```

!!! info "Key observations"

    - Type hints on both the class and the functions let mypy verify their
        interaction statically.
    - Non-optional attributes remove the need for defensive `None` checks in
        functions. They also give mypy enough information to spot dead code.
    - Type checking catches errors before runtime. For validation at runtime,
        consider a library like [pydantic](https://docs.pydantic.dev).

## Reusing functions in other contexts

Comparing the two functions, only `check_for_earthquakes()` relies on
`contains_earthquake`, the one attribute specific to this project. The remaining
attributes form a common baseline, suggesting `detrend()` should work with other
seismogram classes too. To test this, consider a second project that stores the
season alongside seismogram data:

```python title="season_seismogram.py"
--8<-- "docs/snippets/tutorial/season_seismogram.py"
```

1. [`StrEnum`][enum.StrEnum] limits the values a string attribute can take.
2. Much like `NoiseSeismogram`, this class has just one project-specific
    attribute (`season`).

??? tip "Mixin classes"

    Both example classes implement the `end_time` property in exactly the same way.
    With many such classes, that repetition adds up. A *mixin* class collects the
    shared implementation in one place:

    <!-- skip: next -->

    ```python
    --8<-- "src/pysmo/_types/seismogram.py:seismogram-mixin"
    ```

    Both `NoiseSeismogram` and `SeasonSeismogram` can inherit from it and drop their
    own `end_time` property:

    <!-- skip: next -->

    ```python title="season_seismogram_short.py"
    --8<-- "docs/snippets/tutorial/season_seismogram_short.py"
    ```

    1. `end_time` is inherited from `SeismogramEndtimeMixin`, so no implementation
        is needed here.

    Class inheritance brings complications of its own, so mixin classes are best
    kept simple, ideally focused on a single task. Several can be combined on one
    class if needed.

Next comes a script that pairs this new class with the `detrend()` function from
earlier. The `season_detrend_v*.py` scripts that follow are identical apart from
which `functions_v*.py` they import `detrend` from.

```python title="season_detrend_v1.py"
--8<-- "docs/snippets/tutorial/season_detrend_v1.py"
```

This script runs correctly:

```bash
$ uv run season_detrend_v1.py && echo "success!"
success!
```

But mypy flags a type mismatch. `detrend()` expects a `NoiseSeismogram` and is
being passed a `SeasonSeismogram`:

```bash
$ uv run mypy season_detrend_v1.py
season_detrend_v1.py:16: error: Argument 1 to "detrend" has incompatible type "SeasonSeismogram"; expected "NoiseSeismogram"  [arg-type]
```

Type annotations prevent using non-existent attributes, but they do not require
using *all* of them. `detrend()` only touches `data`, which both classes happen
to share. That was luck, not design.

Fixing this means amending the type annotations of the `detrend()` function:

```python title="functions_v3.py" hl_lines="2 13"
--8<-- "docs/snippets/tutorial/functions_v3.py"
```

1. `SeasonSeismogram` has to be imported before it can be used in the
    annotations.

With these changes, mypy reports no errors:

```bash
$ uv run mypy season_detrend_v2.py
Success: no issues found in 1 source file
```

!!! info "Key observations"

    - The `detrend()` function now works in a different context.
    - Reusing it required changing its type annotations.
    - The changes were small, but making them for every new class is cumbersome.
    - `check_for_earthquakes()` is not reusable at all. It relies on
        `contains_earthquake`, which only exists in `NoiseSeismogram`.
    - So there are two kinds of function: those that are reusable and those that are
        not. Their type annotations reflect the difference.

## Introducing pysmo

Writing a custom class for each project is fine. Updating every shared function
whenever a new class appears is not. Each new class means touching function
annotations, and a change to any class risks breaking the functions that depend
on it. The standard solution is an *interface* between functions and classes:
functions target the interface, and classes conform to it.

Pysmo provides such an interface for seismogram (and other) classes. These
interfaces use Python's [`Protocol`][typing.Protocol] class. Below is the actual
implementation of pysmo's [`Seismogram`][pysmo.Seismogram] interface:

```python
--8<-- "src/pysmo/_types/seismogram.py:seismogram-protocol"
```

Strip away the docstrings and this looks much like the common structure of
`NoiseSeismogram` and `SeasonSeismogram`. The key difference is that `end_time`
is declared but not implemented. `Protocol` classes provide type information
only and cannot be instantiated.

!!! note "Why 'types', not 'protocols'"

    Python `Protocol` classes are used almost exclusively in type annotations. This
    documentation therefore calls the ones shipped with pysmo *types* rather than
    protocols or interfaces.

Through structural subtyping, any class with the matching structure is treated
as a subtype of the protocol. Instances of `NoiseSeismogram` and
`SeasonSeismogram` therefore satisfy `Seismogram` as well.

Annotating `detrend()` with the `Seismogram` type rather than listing every
class:

```python title="functions_v4.py" hl_lines="2 13"
--8<-- "docs/snippets/tutorial/functions_v4.py"
```

1. `Seismogram` replaces the import of `SeasonSeismogram`.
2. Any class that satisfies the `Seismogram` structure is now accepted, with no
    further changes to `detrend()`.

With `Seismogram` in place, mypy accepts the season script unchanged:

```bash
$ uv run mypy season_detrend_v3.py
Success: no issues found in 1 source file
```

!!! info "Key observations"

    - `detrend()` now uses a pysmo type in its annotations.
    - Because `NoiseSeismogram` and `SeasonSeismogram` match `Seismogram`, type
        checkers accept their instances as inputs to `detrend()`.
    - Any future seismogram class is accepted too, with no change to `detrend()`, as
        long as it follows the structure `Seismogram` prescribes.
    - `check_for_earthquakes()` stays annotated with `NoiseSeismogram`, because it
        uses `contains_earthquake`, which is not part of `Seismogram`.

## Conclusion

This tutorial introduced the core ideas behind pysmo rather than its API:

- Pysmo is *not* centred on a single seismogram class. Monolithic classes tend
    to reflect the use cases their authors had in mind, not the ones users
    actually have.
- Custom seismogram classes fit specific use cases well, but create friction
    when writing reusable code.
- Pysmo addresses this with interfaces, the *pysmo types*, that capture what
    different classes have in common. Functions target the interface, and any
    conforming class works.
- Pysmo types are intentionally narrow: few attributes, almost no methods.

The same principles apply to the processing modules pysmo ships with, so they
work just as well outside pysmo as within it.

The [Usage](../usage/index.md) chapter goes further: how the types are designed,
the conventions they follow, and how to adapt an existing class to them.
