<!-- invisible-code-block: python 
```python
>>> from pysmo.classes import SacSeismogram
```
-->
# Functions

At this point you have probably seen quite a few examples of functions that
use pysmo types in this documentation. This chapter shows how to use pysmo
types for the type hints in your functions.

## Pysmo types as input

The simplest way of using pysmo types is in functions that only use them as
inputs. In these instances we don't need to be concerned about differences
between different compatible classes, as their "journeys" end here. For
example, the following function takes any [`Seismogram`][pysmo.Seismogram]
compatible object as input, and always returns a [`float`][float] regardless of
what is used as input (e.g. [`MiniSeismogram`][pysmo.MiniSeismogram],
[`SacSeismogram`][pysmo.classes.SacSeismogram], or a custom class):

```python title="double_delta_float.py"
--8<-- "docs/snippets/double_delta_float.py"
```

Because the function output is always a [`float`][float], we don't lose track
of any typing information when the function output is used elsewhere (e.g. in a
function that needs a [`float`][float] as input).

!!! Warning

    Be careful when changing attributes of the input class inside a function.
    Sometimes the attributes are objects that contain other objects (e.g. an
    [`ndarray`][numpy.ndarray] containing [`float`][float] objects). In our
    example above, the `seismogram` we use as input shares the nested objects
    in the `data` attribute with the `seismogram` inside the function. Changing
    `seismgram.data` inside the function will therefore also change it outside
    too. This behavior is often desired, but you must be aware of when this
    occurs and when not.

## Mini classes as output

While it may be perfectly acceptable to use pysmo types as output, we often
lose some typing information when doing so. If we modify the above function to
use a [`Seismogram`][pysmo.Seismogram] for both input and output, we end up not
knowing what exactly was used as input:

```python title="double_delta.py" hl_lines="25-26"
--8<-- "docs/snippets/double_delta.py"
```

1. `reveal_type` allows us to inspect the actual type of an object. It prints
  type information at runtime (what it actually is) or when using mypy (what
  can be inferred from type annotations).
2. :bulb: Deep copying objects can be expensive if they contain large nested
  items.

The highlighted lines in the code above produce the following output when the
script is executed:

<!-- skip: next -->

<!-- termynal -->

```bash
$ python double_delta.py
Runtime type is 'SacSeismogram'
Runtime type is 'SacSeismogram'
```

This tells us that at runtime `my_seis_in` and `my_seis_out` are both of type
[`SacSeismogram`][pysmo.classes.SacSeismogram]. Running mypy on the code,
however, yields a different type for `my_seis_out`:

<!-- termynal -->

```bash
$ mypy double_delta.py
docs/snippets/double_delta.py:26: note: Revealed type is "SacSeismogram"
docs/snippets/double_delta.py:27: note: Revealed type is "Seismogram"
Success: no issues found in 1 source file
```

This discrepancy is due the fact that our function is annotated in a way that
tells us any [`Seismogram`][pysmo.Seismogram] is acceptable as input, and that
a [`Seismogram`][pysmo.Seismogram] is returned, but we don't know *which* type
exactly that is going to be.

!!! tip

    A modern editor may display type information without running mypy:

    ![reveal type](../images/func_reveal_dark.png#only-dark){ loading=lazy }
    ![reveal type](../images/func_reveal_light.png#only-light){ loading=lazy }

This loss of information is often not a problem, but if you do intend to use
the output of such a function for further processing, it might be better to be
explicit about they type of output. Since all pysmo types have a corresponding
Mini class, one strategy is to use those as output types:

```python title="double_delta_mini.py"
--8<-- "docs/snippets/double_delta_mini.py"
```

1. Here we use the [`clone_to_mini`][pysmo.functions.clone_to_mini] function
  to create a [`MiniSeismogram`][pysmo.MiniSeismogram] instances from other
  [`Seismogram`][pysmo.Seismogram] instances. It is typically faster than deep
  copying because it only copies the attributes that are actually used.

## Type preservation

Another option to be explicit about the output type of a function is to declare
that the input type has to be the same as the output type. For pysmo types this
requires two things:

1. We need to save the input type as variable which we can reference for the
  output type.
2. We need to place bounds on this variable so that it is limited to the
  desired pysmo type(s).

This typing strategy involves
[generics](https://mypy.readthedocs.io/en/stable/generics.html), and changes
our function to the following:

```python title="double_delta_generic.py" hl_lines="7"
--8<-- "docs/snippets/double_delta_generic.py"
```

1. :bulb: This syntax is only valid for Python versions 3.12 and above.

In our example `[T: Seismogram]` defines a type variable `T` that has to be a
[`Seismogram`][pysmo.Seismogram]. We then use `T` as before to annotate the
function. This means that if we use it with e.g. a
[`MiniSeismogram`][pysmo.MiniSeismogram] as input, `T` is set to
[`MiniSeismogram`][pysmo.MiniSeismogram] and the function signature effectively
becomes:

```python
def double_delta_generic(seismogram: MiniSeismogram) -> MiniSeismogram:
  ...
```

Or if we use a [`SacSeismogram`][pysmo.classes.SacSeismogram]:

```python
def double_delta_generic(seismogram: SacSeismogram) -> SacSeismogram:
  ...
```

which is also what we used for our example. Therefore, running `mypy` on
`double_delta_generic.py` gives:

<!-- termynal -->

```bash
$ mypy double_delta_generic.py
double_delta_generic.py:25: note: Revealed type is "SacSeismogram"
double_delta_generic.py:26: note: Revealed type is "SacSeismogram"
Success: no issues found in 1 source file
```

Crucially, because `T` has an
[upper bound](https://mypy.readthedocs.io/en/stable/generics.html#type-variables-with-upper-bounds)
(in this case [`Seismogram`][pysmo.Seismogram]),
we get all the usual benefits from type hints while coding (autocompletion,
error checking, etc.).
