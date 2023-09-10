# Rules of the Land

Regardless of whether you plan on introducing changes (or new code) to pysmo just for
yourself, or want to contribute back to pysmo at some point, it makes sense to understand
the project organisation, conventions, and tools used.


## What goes where

For the most part, the same components presented to a pysmo user
([Types](../user-guide/types.md), [Classes](../user-guide/classes/index.md),
[Functions](../user-guide/functions.md), [Tools](../user-guide/tools/index.md))
are also how the code itself is organised. It should be fairly easy to determine where a
new piece of code should go. Keep in mind that types, classes, and functions are treated
as a single module, and therefore any additions need to be reflected in the contents of
the `pysmo/__init__.py` file. Tools are all separate modules, and therefore either don't
need an `__init__.py` file at all (if they consist of a single file), or their own
independent one.

## Types

Types are at the core of pysmo, and all other parts of pysmo depend on them. Stability
(by that we mean never having to change their behavior in future updates) is therefore
paramount. This ensure continued stability, please:

- **Don't declare methods:** While protocol classes certainly allow for methods
  to be declared, we don't think they make much sense for how protocol classes
  are used in pysmo. A pysmo type should declare what a thing *is*, not what
  it can do.
- **Avoid using [`Optional`][typing.Optional] attributes:** In most cases,
  allowing attributes to be [`None`][None] means the types become meaningless.
  For example, a [`Location`][pysmo.types.Location] where coordinates
  are optional doesn't really make sense.
- **Reuse existing types:** as the protocols contain only the typing structure,
  they can quite easily inherit from each other. If a new type were to
  contain all attributes of an existing type, that existing type should be
  reused. For example:
  ```python title="type_A_B.py"
  class A(Protocol):
    """Pysmo type A, which has properties prop1 and prop2."""
    @property
    def prop1(self):
      ...

    @property
    def prop2(self):
      ...

  class B(A, Protocol):
    """Pysmo type B, which has properties prop1, prop2, and prop3."""
    @property
    def prop3(self):
      ...
  ```
- **Don't confuse data grouping with a type:** Just because it makes sense
  to group data a certain way (e.g. the way we present data in the
  [`SAC`][pysmo.classes.sac.SAC] class to make it work with pysmo types),
  doesn't mean that a type is needed for that group. Remember, any class
  may be a subclass of any number of protocols.
- **Mini classes:** Every type should have a corresponding minimal
  generic class (see more below).
- **Documentation:** pysmo types are documented in the docstrings of
  the `.py` files. No changes are required in the documentation
  files to include new types.


## Classes

The generic classes serve as containers for data, which are used via the pysmo types.
When writing a new class (or modifying an existing one to become compatible with
pysmo), it is important to remember that the pysmo types are protocol classes, and as
such only check for type compatibility. It is therefore up to the programmer to ensure
they behave as expected (which may be verified using the unit tests provided by pysmo).
The classes are similarly essential to pysmo as the types, and similar rules apply:

- **Exact signature:** If a class is meant to work with a pysmo type, its type
  signature needs to be the exactly the same. For example, if an attribute
  defined by a type is a [`float`][float], you may not use
  [`float`][float]`|`[`None`][None] for that attribute.
- **Mini Classes:** For each type there is a corresponding "mini" class (e.g.
  [`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] for the
  [`Seismogram`][pysmo.types.Seismogram] type). They serve as a sort of
  reference implementation and as default types for functions that output
  data (where applicable). These mini classes should not have any attributes
  that are not in the corresponding protocol classes, though they may include
  extra methods.
- **Documentation:** Classes should be completely documented within their
  docstrings. However, a small markdown file needs to be added to
  [docs/user-guide/classes](https://github.com/pysmo/pysmo/tree/master/docs/user-guide/classes)
  for the documentation to included here.


## Functions

Items that belong to this category are basic functions that typically operate on pysmo
types. It is not a hard requirement that functions defined here always use pysmo types,
but if you do write a function that *doesn't* use pysmo types, it is worth asking
yourself if perhaps it is worth defining a new type, or if it makes more sense to add
your function to one of the [tools](#tools) modules. Considerations for functions:

- **Return types:** if the output type of a function is a pysmo type, please use
  use the corresponding [mini](../user-guide/classes/minimal.md) class instead
  of e.g. [deep-copying][copy.deepcopy] the input object.
- **Consider adding a method:** Especially for things like seismogram data, it
  will often be the case that the output of a function is used to overwrite
  the input (e.g. when doing something like detrending data). In such instances
  it makes sense to also add a method to the mini class (and use it inside the
  function).
- **Documentation:** pysmo functions are documented in the docstrings of
  the `.py` files. No changes are required in the documentation
  files to include new functions.


## Tools

Tools is a place where we group topical functions together (e.g. for things like signal
processing). It also may serve as a place for "anything else".

- **Tools are modules:** Each tool should be it's own module, that can be imported
  as `pysmo.tools.<toolname>`. Therefore, tools that exist in a single file
  don't need a `__init__.py` file, and ones that exist in their own directory
  need an `__init__.py` file in that directory.
- **Documentation:** Each tool's documentation should also be entirely within
  the module as docstrings. A markdown file needs to be added to
  [docs/user-guide/tools](https://github.com/pysmo/pysmo/tree/master/docs/user-guide/tools).


## Testing

Testing may present a chicken and egg type of situation, where the reference test data
are calculated from the code that is being tested itself. While this does help avoid
future code changes from breaking things, there is no way to know if the initial code is
actually correct (e.g. free from logical errors). Ideally, test data should therefore be
calculated using external tools. Where this is not possible, we suggest writing tests
that involve creating figures (with [matplotlib][]) that can be manually inspected to see
if the output makes sense. These figures then become the reference data that future test
runs can use via the [pytest-mpl][] extension automatically.


## Formatting and Style

### Code

Adhering to python conventions such as [PEP 8](https://peps.python.org/pep-0008/) and
linting code with e.g. [flake8](https://flake8.pycqa.org/en/latest/) results in clean and
easily readable code. Aside from using those kinds of tools, we highly encourage writing
[self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code). For
example, instead of writing code to calculate velocity like this:

```python title="documented-code.py"
# Calculate the velocity v
def v(d: float, t: float) -> float:
  """Calculates the velocity from distance and time."""
  # distance is d
  # time is t
  return d / t
```

Use of more meaningful variable (and function) names results in code that is easier to
read and less error prone (e.g. due to ambiguous variable names causing confusion):

```python title="self-documenting-code.py"
def velocity(distance: float, time: float) -> float:
  """Calculates the velocity from distance and time."""
  return distance / time
```

### Documentation

This documentation is built using [mkdocs](https://www.mkdocs.org/) using the
[material](https://squidfunk.github.io/mkdocs-material/) theme. Thus the main
documentation source files are written in
[Markdown](https://en.wikipedia.org/wiki/Markdown). The docstrings in the `.py` files are
included via the [mkdocstrings](https://mkdocstrings.github.io) plugin. Please write the
docstrings using the
[google](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
style.
