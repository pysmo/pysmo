---
icon: lucide/square-function
tags:
  - Functions
  - Usage
---

<!-- invisible-code-block: python 
```python
>>> from pysmo.classes import SacSeismogram
```
-->

# Functions

Writing functions is the most common way of using pysmo. Whatever a function
does, it will usually follow one of the patterns below.

## Mutable objects

First, a reminder of how Python handles objects passed to functions. Python
passes objects by reference, not by value: a function receives the *same* object
as the caller, not a copy. For immutable types like [`int`][] or [`float`][]
this rarely matters. For mutable objects such as
[`numpy.ndarray`][numpy.ndarray] it matters a great deal:

```python
>>> import numpy as np
>>> def double_first(array):
...     array[0] *= 2
...
>>> my_array = np.array([1.0, 2.0, 3.0])
>>> double_first(my_array)
>>> my_array
array([2., 2., 3.])
```

The array was modified *inside* the function, yet the change is visible
*outside* it: both the caller and the function hold a reference to the same
object. This is sometimes the intent, but it needs to be a deliberate choice.
The `clone` argument below comes back to this.

## Pysmo types as input

The simplest use of pysmo types is in functions that only use them to annotate
inputs. Differences between the compatible classes cannot affect the rest of the
program, because the object goes no further than this function.

The following function takes any [`Seismogram`][pysmo.Seismogram]-compatible
object and returns a [`Timedelta`][pandas.Timedelta]:

```python title="double_delta_td.py"
--8<-- "docs/snippets/double_delta_td.py"
```

Nothing here needs a pysmo type in the return position, so annotating the output
is straightforward. That changes as soon as a function returns one of its
pysmo-typed inputs.

## Pysmo types as output

It gets more complicated when a function returns the data it accepted as input.
Annotating the input with `Seismogram` accepts any compatible type, but that
same flexibility means the exact output type is unknown. The following snippet
shows the problem:

```python title="double_delta.py" hl_lines="28-29"
--8<-- "docs/snippets/double_delta.py"
```

1. [`reveal_type`][typing.reveal_type] inspects the type of an object. It prints
    the runtime type when run directly, or the inferred type when run through
    mypy.
2. :bulb: As noted [above](#mutable-objects), passing an object to a function
    does not copy it. [`deepcopy`][copy.deepcopy] is used here to make an
    independent copy before modifying it, leaving the caller's object
    untouched. Pysmo functions that modify seismograms offer this through a
    `clone` argument. Deep-copying can be expensive for large objects.

The snippet creates a [`SacSeismogram`][pysmo.classes.SacSeismogram] instance
from a SAC file and passes it to `double_delta`. Inside the function it is
deep-copied, modified, and returned as the same type. Running the script, the
highlighted lines produce:

<!-- skip: next -->

```bash
$ uv run double_delta.py
Runtime type is 'SacSeismogram'
Runtime type is 'SacSeismogram'
```

At runtime, `my_seis_in` and `my_seis_out` are both `SacSeismogram`. Running
mypy on the same code gives a different type for `my_seis_out`:

```bash
$ uv run mypy double_delta.py
double_delta.py:28: note: Revealed type is "SacSeismogram"
double_delta.py:29: note: Revealed type is "Seismogram"
Success: no issues found in 1 source file
```

The annotation says any `Seismogram` is acceptable as input and that a
`Seismogram` is returned, but not which concrete type. This loss of type
information is sometimes acceptable, but it is not ideal.

## Mini classes as output

Return types matter because the output of one function is often the input to the
next. When chaining functions that use pysmo types, a "Mini" class is a good
choice of return type. These minimal implementations of the pysmo types are
simple and efficient. With one, `double_delta` becomes:

```python title="double_delta_mini.py"
--8<-- "docs/snippets/double_delta_mini.py"
```

1. [`clone_to_mini`][pysmo.functions.clone_to_mini] creates a
    [`MiniSeismogram`][pysmo.MiniSeismogram] from any `Seismogram`. It is
    usually faster than deep-copying.

This allows the data to be copied to a Mini instance early, processed through
several steps on that efficient instance, and copied back to the original data
source at the end.

A Mini return type deliberately changes the type. To hand back the caller's
exact type instead, use a generic.

## Same input and output type

Another way to pin down the output type is to require that the input and output
types match, preserving whatever concrete type the caller passed in. For pysmo
types this needs two things:

1. Save the input type in a variable that the output type can reference.
2. Bound that variable so it is limited to the intended pysmo type or types.

This strategy uses
[generics](https://mypy.readthedocs.io/en/stable/generics.html), and changes the
function to:

```python title="double_delta_generic.py" hl_lines="9"
--8<-- "docs/snippets/double_delta_generic.py"
```

1. :bulb: This syntax is only valid for Python 3.12 and above.

`[T: Seismogram]` defines a type variable `T` bound to `Seismogram`, and `T`
then annotates the function. Passing a `MiniSeismogram` instance as `seismogram`
sets `T` to `MiniSeismogram`, so the signature effectively becomes:

```python
def double_delta_generic(seismogram: MiniSeismogram) -> MiniSeismogram:
  ...
```

Or with a `SacSeismogram` instance:

```python
def double_delta_generic(seismogram: SacSeismogram) -> SacSeismogram:
  ...
```

The example uses a `SacSeismogram`, so running `mypy` on
`double_delta_generic.py` gives:

```bash
$ uv run mypy double_delta_generic.py
double_delta_generic.py:28: note: Revealed type is "SacSeismogram"
double_delta_generic.py:29: note: Revealed type is "SacSeismogram"
Success: no issues found in 1 source file
```

Because `T` has an
[upper bound](https://mypy.readthedocs.io/en/stable/generics.html#type-variables-with-upper-bounds)
(here `Seismogram`), the usual type-hint benefits still apply while coding:
autocompletion, error checking, and so on.

## Output type depends on input parameter

The previous two sections tie the return type to the *type* of an argument. A
return type can also depend on the *value* of an argument. Annotating such a
function needs the [`overload`][typing.overload] decorator to declare every
possible combination. The pysmo [`detrend`][pysmo.functions.detrend] function
uses this:

<!-- skip: next -->

```python
--8<-- "src/pysmo/functions/_seismogram.py:detrend"
```

The `detrend` function looks like it is declared several times. At runtime the
`@overload` decorator tells Python to ignore the decorated declarations; they
are only for type checkers. Read from *bottom to top*:

- `detrend` takes two arguments. The type of `seismogram` is captured in the
    variable `T` (bound by `Seismogram`), and `clone` is a [`bool`][] defaulting
    to [`False`][]. The function returns either [`None`][] or a value of type
    `T`.
- If `clone` is [`True`][], an object of type `T` is returned.
- If `clone` is `False` (the default), `None` is returned. `T` is not needed
    here: it is not reused elsewhere in this declaration, so a type variable
    serves no purpose.

!!! tip "Overloads get easier"

    The patterns repeat, and overloaded declarations can largely be copied from one
    function to the next. The time spent writing them is usually less than the time
    lost to the bugs they prevent.

## Choosing a return type

- A function that only **accepts** pysmo types needs nothing special: annotate
    the inputs and return whatever suits.
- A function that **returns** a pysmo-typed object has three options:
  - Return a Mini class when a canonical, efficient type is acceptable. This
        suits chains of several functions.
  - Use a generic (`[T: Seismogram]`) when the caller's exact type must be
        preserved.
  - Use `overload` when the return type depends on the value of an argument,
        such as `clone`.
