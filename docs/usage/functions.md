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

Writing functions is the easiest and most common way of using pysmo. Regardless
of what the functions do, they will most likely follow one of the patterns
discussed below.

## Pysmo types as input

The simplest way of using pysmo types is in functions that only use them to
annotate inputs. In these instances we don't need to be concerned about how
differences between different compatible classes affect other parts of your
code, as their "journeys" end here.

For example, the following function takes any [`Seismogram`][pysmo.Seismogram]
compatible object as input, and returns a [`timedelta`][datetime.timedelta]:

```python title="double_delta_td.py"
--8<-- "docs/snippets/double_delta_td.py"
```

!!! Warning

    Be careful when changing attributes of the input class inside a function.
    Sometimes the attributes are objects that contain other objects (e.g. an
    [`ndarray`][numpy.ndarray] containing [`float`][float] objects). In our
    example above, the `seismogram` we use as input shares the nested objects
    in the `data` attribute with the `seismogram` inside the function. Changing
    `seismogram.data` inside the function will therefore also change it outside
    too. This behaviour is often desired, but you must be aware of when this
    occurs and when not.

## Pysmo types as output

It gets more complicated when a function returns the data it accepted as input
(annotated with a pysmo type). While using [`Seismogram`][pysmo.Seismogram] to
annotate the input allows us to accept any number of different input types,
that same flexibility means we cannot be certain of what exactly the output
type is. We can explore this with the following snippet:

```python title="double_delta.py" hl_lines="27-28"
--8<-- "docs/snippets/double_delta.py"
```

1. [`reveal_type`][typing.reveal_type] allows us to inspect the actual type of an object. It prints
  type information at runtime (what it actually is) or when using mypy (what
  can be inferred from type annotations).
2. :bulb: Deep copying objects can be expensive if they contain large nested
  items.

Here, we create a [`SacSeismogram`][pysmo.classes.SacSeismogram] instance from
a SAC file and pass it to the `double_delta` function. Inside the function it
gets [deepcopied][copy.deepcopy], modified and returned as the same type. We
can verify this by executing the script, whereby the highlighted lines in the
code produce the following output:

<!-- skip: next -->

```bash
$ python double_delta.py
Runtime type is 'SacSeismogram'
Runtime type is 'SacSeismogram'
```

As suspected, `my_seis_in` and `my_seis_out` are both of type
[`SacSeismogram`][pysmo.classes.SacSeismogram] at runtime. Running mypy on the
code, however, yields a different type for `my_seis_out`:

```bash
$ mypy double_delta.py
docs/snippets/double_delta.py:26: note: Revealed type is "SacSeismogram"
docs/snippets/double_delta.py:27: note: Revealed type is "Seismogram"
Success: no issues found in 1 source file
```

This discrepancy is due to the fact that our function is annotated in a way that
tells us any [`Seismogram`][pysmo.Seismogram] is acceptable as input, and that
while a [`Seismogram`][pysmo.Seismogram] is returned, we cannot know which type
*exactly* that is going to be. While this loss of typing information may be
acceptable for your use case, it is certainly far from ideal.

## Mini types as output

The reason return types need to be specified, is because the output of one
function can also be used as input for other functions. If you are chaining
together multiple functions using pysmo types, you may want to consider using
"Mini" types as output. These minimal implementations of pysmo type compatible
classes are simple and efficient. The `double_delta` function would look like
this:

```python title="double_delta_mini.py"
--8<-- "docs/snippets/double_delta_mini.py"
```

1. Here we use the [`clone_to_mini`][pysmo.functions.clone_to_mini] function
  to create [`MiniSeismogram`][pysmo.MiniSeismogram] instances from other
  [`Seismogram`][pysmo.Seismogram] instances. It is typically faster than deep
  copying.

With this approach you could copy your data to a Mini instance early on in your
processing, perform multiple processing steps on the efficient Mini instance,
and in a last step copy the processed data back to your original data source.

## Same input and output type

Another option to be explicit about the output type of a function, is to
declare that both the input and output types have to be the same. For pysmo
types this requires two things:

1. We need to save the input type as variable which we can reference for the
  output type.
2. We need to place bounds on this variable so that it is limited to the
  desired pysmo type(s).

This typing strategy involves
[generics](https://mypy.readthedocs.io/en/stable/generics.html), and changes
our function to the following:

```python title="double_delta_generic.py" hl_lines="8"
--8<-- "docs/snippets/double_delta_generic.py"
```

1. :bulb: This syntax is only valid for Python versions 3.12 and above.

In our example `[T: Seismogram]` defines a type variable `T` that has to be a
[`Seismogram`][pysmo.Seismogram]. We then use `T` as before to annotate the
function. This means that if we use it with e.g. an instance of
[`MiniSeismogram`][pysmo.MiniSeismogram] as input for `seismogram`, `T` is set
to [`MiniSeismogram`][pysmo.MiniSeismogram] and the function signature
effectively becomes:

```python
def double_delta_generic(seismogram: MiniSeismogram) -> MiniSeismogram:
  ...
```

Or if we use a [`SacSeismogram`][pysmo.classes.SacSeismogram] instance:

```python
def double_delta_generic(seismogram: SacSeismogram) -> SacSeismogram:
  ...
```

which is also what we used for our example. Therefore, running `mypy` on
`double_delta_generic.py` gives:

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

## Output type depends on input parameter

Admittedly, things can get rather complex when input and output types of a
function depend on each other. Properly annotating such a function requires
using the [`overload`][typing.overload] decorator to declare all possible type
combinations that may occur. The pysmo [`detrend`][pysmo.functions.detrend]
function makes use of this feature:

<!-- skip: next -->

```python
--8<-- "src/pysmo/functions/_seismogram.py:detrend"
```

Here it looks as if the `detrend` function is declared multiple times. However,
at runtime the `@overload` decorator tells Python to ignore that particular
function declaration, as it is only meant to be used by type checkers. Looking
at the declarations from *bottom to top* we read it as follows:

- The function `detrend` takes two arguments, `seismogram` and `clone`,
  whereby the type of `seismogram` is stored in the variable `T` (bound by
  [`Seismogram`][pysmo.Seismogram]), and `clone` is a [`bool`][] with a default
  value of [`False`][]. The function returns either a [`None`][] or `T` type.
- If `clone` is [`True`][], then an object of type `T` is returned.
- If `clone` is [`False`][] (the default value), then [`None`][] is returned.
  Note that we don't need to use `T` here; as we don't reuse `T` elsewhere in
  this function declaration, it doesn't make much sense to use a type variable
  in the first place.

!!! tip

    This may seem a bit overwhelming at first, but you will quickly find that
    the patterns frequently repeat themselves, and that you can simply copy
    paste a lot of the overloaded function declarations. Remember also that the
    time invested here likely more than offsets the amount of time spent
    hunting down avoidable bugs in your code.
