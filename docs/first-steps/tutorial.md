---
icon: lucide/graduation-cap
---

# Tutorial

In this tutorial, we will walk through a simple example of how pysmo can be
used in a project. This will provide insight into:

- How to define a new seismogram class that is tailored to a specific use case
  (and why you would want to do that).
- How to use this new class together with pysmo.
- Writing new code that is potentially reusable by other projects or classes.

## Custom seismogram class

The purpose of a class in Python is generally to store state (i.e. data). As the
exact type of data can vary between use cases, it is often useful to define a
new class that is tailored to the specific scenario.

We will assume that our use case here is to store seismogram data that is to be
used in an ambient noise cross-correlation project. In this context, we don't
need to store event information in our seismograms. In fact, we are probably
more interested in knowing whether or not earthquake signals are present in
the seismogram data. We would therefore want our class to have an attribute to
store this particular piece of information. A simple class definition could
look like this:

```python title="noise_seismogram.py"
--8<-- "docs/snippets/tutorial/noise_seismogram.py"
```

1. [`dataclass`][dataclasses.dataclass] is a decorator that automatically
   generates special methods for the class, such as `__init__`, `__repr__`, and
   `__eq__`, based on the class attributes. This makes it easier to create
   classes that are primarily used to store data.
2. Instance attributes are defined simply by declaring them in the class body
   with type annotations.
3. Attributes can have default values too.
4. Care must be given if default values are mutable types (like lists or
   dictionaries). In such cases, you need to use `field(default_factory=...)` to
   ensure that each instance of the class gets its own separate copy of the
   mutable object.
5. A `__len__` method is a special method that lets us use the built-in
   [`len()`][len] function, defined here as the number of samples in the data
   array.
6. We add a read-only property `end_time` that computes the end time of the
   seismogram based on the start time, number of samples, and sampling rate.
7. Finally, we add an attribute that lets us know if our seismogram contains
   earthquake signals or not.

A real world example would likely have more attributes (such as station
coordinates), but to keep things simple we will stick to this minimal example.

We are now ready to use this new class in our project. To test this run an
interactive Python session and create an instance of the class:

```bash
$ python -i noise_seismogram.py
>>> begin_time = datetime(2023, 1, 1, 0, 0, 0)
>>> data = np.random.randn(1000)  # Simulated noise data
>>> noise_seis = NoiseSeismogram(begin_time=begin_time, data=data)
>>>
```

!!! info "Key observations"

    - Creating a purpose-built class whose primary purpose is to store data is
      simple and straightforward with the [`dataclass`][dataclasses.dataclass]
      decorator.
    - With the exception of the `__len__` method (which allows using
      [`len`][len] on `NoiseSeismogram` instances), we have not defined any
      methods in our class.
    - All attributes of the class are non-optional. If they were, we would
      have typed them with e.g. `bool | None` instead of just `bool`.
      While this is not strictly a requirement, it does avoid having to deal
      with the possibility of multiple instances of the class having different
      amounts of data (e.g. some instances having information in the
      `contains_earthquake` attribute and some not). This simplifies things
      later on, as we don't need to include checks for the presence of data in
      our functions.

## Functions that operate on the new class

Now that we have our new class to store seismogram data, we likely want to do
some form of processing on the data. In this example, we will write two
functions:

- `check_for_earthquakes()`: A function that checks if earthquake signals are
  present in the seismogram data.
- `detrend()`: A function that detrends the seismogram data.

A first version of these functions could look like this:

```python title="functions_v1.py" hl_lines="11"
--8<-- "docs/snippets/tutorial/functions_v1.py"
```

These functions are already pretty good. They are easy to understand and are
properly annotated with type hints. We can verify this by checking the file
with [mypy](https://mypy.readthedocs.io):

```bash
$ python -m mypy functions_v1.py
Success: no issues found in 1 source file
```

Checking code with mypy is a great way to prevent errors from sneaking into
your codebase. Most modern code editors have the same type of checking built
in, so it is really easy to make use of type hints in this way. If we really
commit to checking all our code while writing it, we can simplify the functions
by stripping out the bits that are unreachable. Running mypy again, but with an
extra flag we can see where this is the case:

```bash
$ python -m mypy --warn-unreachable functions_v1.py
functions_v1.py:11: error: Statement is unreachable  [unreachable]
Found 1 error in 1 file (checked 1 source file)
```

We get this error because the `contains_earthquake` attribute is non-optional,
so it can only be `True` or `False`. This means that the `else` branch of the
function (highlighted in the code block above) is never used and can be
removed:

```python title="functions_v2.py" hl_lines="8 9"
--8<-- "docs/snippets/tutorial/functions_v2.py"
```

1. At this point we know that `seismogram.contains_earthquake` can only be
   `False`, so we don't need an `elif` check anymore.

Mypy is also happy with this version of the code:

```bash
$ python -m mypy --warn-unreachable functions_v2.py
Success: no issues found in 1 source file
```

!!! info "Key observations"

    - Writing functions for our bespoke class is also pretty straightforward.
    - Because we have correctly annotated both our class and our functions with
      type hints, we can easily check our code for errors with mypy.
    - Our purpose-built class avoids optional attributes, which allows us to
      avoid redundant checks in our functions. This makes our code simpler and
      likely easier to read.
    - Note that we are relying on checking our code before running it! If you
      want checking at runtime, you may need to look into using a library like
      [beartype](https://beartype.readthedocs.io) or
      [pydantic](https://docs.pydantic.dev).

## Reusing functions in other contexts

Comparing the two functions, `check_for_earthquakes()` and `detrend()`, we notice
that only the former relies on the `contains_earthquake` attribute of our
class. Recall that this attribute was the only one introduced for the specific
use case of ambient noise cross-correlation. This means that the remaining
attributes form a sort of "baseline" seismogram, that we are likely to
encounter in other use cases as well. Put another way, we ought to be able to
reuse the `detrend()` function in other contexts.

To illustrate this, let's consider a different project, where we (for some
reason) want to store the season together with seismogram data. Again we write
a bespoke class for this:

```python title="season_seismogram.py"
--8<-- "docs/snippets/tutorial/season_seismogram.py"
```

1. [`StrEnum`][enum.StrEnum] are a great way to limit the values strings can
   take.
2. Much like with `NoiseSeismogram`, we have just one project specific
   attribute (`season`).

Next we write a script that uses this new class together with the `detrend()`
function from earlier:

```python title="season_detrend_v1.py"
--8<-- "docs/snippets/tutorial/season_detrend_v1.py"
```

This script will actually run without a hitch:

```bash
$ python season_detrend_v1.py && echo "success\!"
success!
```

However, because we have a mismatch in our type annotations (`detrend()`
expects a `NoiseSeismogram` but we are passing it a `SeasonSeismogram`), mypy
will complain:

```bash
$ python -m mypy season_detrend_v1.py
season_detrend_v1.py:16: error: Argument 1 to "detrend" has incompatible type "SeasonSeismogram"; expected "NoiseSeismogram"  [arg-type]
```

The reason for this discrepancy is that type annotations prevent us from using
non-existent attributes in our functions, but that doesn't mean we have to use
*all* available attributes. In this case, the `detrend()` function only relies
on the `data` attribute, which happens to exist in both `NoiseSeismogram` and
`SeasonSeismogram`. In other words, we just got lucky this time.

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

If we are sold on the idea of writing custom seismogram classes for particular
use cases, we end up with a bit of a maintenance nightmare if we have a lot of
"shared" type functions. As shown by the `detrend()` function, whenever we want
existing functions to work smoothly with a new class, we need to use it to
annotate the function. Doing this also introduces a dependency between the
functions and classes. It is therefore conceivable that sometime in the future
one of the classes may change in a way that breaks functions.

This is not a new problem in programming, and is typically solved by defining
interfaces that sit between the functions and the classes (or more generally
between different parts of code). This means that we can write a function to be
compatible with the interface rather than multiple different (seismogram)
classes. Of course, the classes need to be written in a way that conforms to the
interface too.

Pysmo provides such an interface for seismogram (and other) classes. These
interfaces make use of Python's [`Protocol`][typing.Protocol] class. Below is
the actual implementation of pysmo's [`Seismogram`][pysmo.Seismogram] interface:

<!-- skip: next -->

```python
--8<-- "src/pysmo/_types/_seismogram.py:seismogram-protocol"
```

If you strip away the extra docstrings, you will notice that this looks
remarkably similar to the common bits of the `NoiseSeismogram` and
`SeasonSeismogram` classes we defined above. Important to mention at this point
is that the `__len__` method and `end_time` property do not really need to be
implemented here. Typically the `__len__` method would look more like this:

```python
def __len__(self) -> int: ...
```

That is because the purpose of [`Seismogram`][pysmo.Seismogram] is mainly to
provide type information - it is actually impossible to create an instance from
a [`Protocol`][typing.Protocol] class directly. However, it is possible to
inherit from them, so we could rewrite the `SeasonSeismogram` as follows:

```python title="season_seismogram_short.py"
--8<-- "docs/snippets/tutorial/season_seismogram_short.py"
```

1. `__len__` and `end_time` are inherited from `Seismogram`, so we don't need
   to write an implementation anymore.

The `NoiseSeismogram` class could be shortened in the same manner.

!!! note

    Python [`Protocol`][typing.Protocol] classes are used almost exclusively in
    type annotations. We will therefore refer to the ones shipped with pysmo as
    *types* rather than protocols or interfaces.

Python considers classes that have the same structure as a protocol class to be
subclasses of the protocol class. For our particular case, this means that
instances of `NoiseSeismogram` and `SeasonSeismogram` are also instances of
`Seismogram`.

Using pysmo types to annotate our functions, even if they are to be used with
loads of different seismogram classes, is now a breeze:

```python title="functions_v4.py" hl_lines="2 13"
--8<-- "docs/snippets/tutorial/functions_v4.py"
```

1. Instead of importing `SeasonSeismogram`, we now import `Seismogram`.
2. We no longer need to list all the seismogram classes we want to use in the
   `detrend` function. We simply specify `Seismogram` and are done.

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

This tutorial doesn't actually show much "pysmo code". Instead it introduces
core concepts of pysmo. These are:

- Pysmo is *not* centred around a single seismogram class that is used as the
  core of the library. Often these kinds of single purpose classes restrict
  users to the use cases envisioned by the library authors, rather than being
  well suited for new applications.
- Custom seismogram classes *are* suited for new applications. However, they
  introduce challenges when trying to write reusable code.
- Pysmo provides a solution for this by focusing on what the different custom
  classes have in common, and defining an interface that can be targeted when
  writing code.
- These interfaces are referred to as *pysmo types*. One of their most defining
  characteristics is that they are very simple (very few attributes, and
  methods are almost entirely avoided).

Pysmo itself is guided by these same principles. Thus, modules packaged with
pysmo are easily reusable in other projects.
