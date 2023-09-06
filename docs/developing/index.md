# Rules of the Land

Regardless of whether you plan on introducing changes (or new code) to pysmo just for
yourself, or want to contribute back to pysmo at some point, it makes sense to understand
the project organisation, conventions, and tools used.


## What goes where

For the most part, the same components presented to a pysmo user
([Types](../user-guide/types.md), [Classes](../user-guide/classes/index.md),
[Functions](../user-guide/functions.md), [Tools](../user-guide/tools/index.md))
are also how the code itself is organised. It should be fairly easy to determine where a
new piece of code should go. However, there are some rules that need to be kept in mind
in order to ensure code added to pysmo behaves as expected.

### Types

Types are at the core of pysmo, and all other parts of pysmo depend on them. Stability
(by that we mean never having to change their behavior in future updates) is therefore
paramount. This stability is achieved by keeping the type definitions simple, and as
close as possible to whatever they represent in the physical world. Other rules to follow
are:

- Types should be top level importable (i.e. `from pysmo import <type>`). Any new type
  should therefore be added to the
  [`pysmo/__init__.py`](https://github.com/pysmo/pysmo/blob/master/pysmo/__init__.py)
  file.
- They should be fully documented inside the docstrings of the `.py` files.
- Every type should have a corresponding minimal generic class (see more below).
- If a new type were to contain all attributes of an existing type, that existing type
  should be reused. For example:

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

### Classes

The generic classes serve as containers for data, which are used via the pysmo types.
When writing a new class (or modifying an existing one to become compatible with
pysmo), it is important to remember that the pysmo types are protocol classes, and as
such only check for type compatibility. It is therefore up to the programmer to ensure
they behave as expected (which is verified using the unit tests provided by pysmo).
The classes are similarly essential to pysmo as the types, and similar rules apply:

- Classes should also be top level importable
  (i.e. `from pysmo import <class>`). Any new class should therefore be added
  to the
  [`pysmo/__init__.py`](https://github.com/pysmo/pysmo/blob/master/pysmo/__init__.py)
  file.
- A markdown file needs to be added to [docs/user-guide/classes](https://github.com/pysmo/pysmo/tree/master/docs/user-guide/classes)
  for the documentation to include the docstrings of the class.
- For each type there is a corresponding minimal class (e.g.
  [`MiniSeismogram`][pysmo.classes.mini.MiniSeismogram] for the
  [`Seismogram`][pysmo.types.Seismogram]). They serve as default class for functions that
  output data. These minimal classes are also where methods are defined. As the methods
  only make use of attributes defined by pysmo types, using the mini classes as base
  class for other classes (compatible with pysmo types) is a potential option.


### Functions

Items that belong to this category are basic functions that typically operate on pysmo
types. It is not a hard requirement that functions defined here always use pysmo types,
but if you do write a function that *doesn't* use pysmo types, it is worth asking
yourself if perhaps it is worth defining a new type. Again there are rules for how
functions are imported:

- Pysmo functions, like types and classes are imported at the base level.
  (i.e. `from pysmo import <function>`). Any new function should therefore be added
  to the
  [`pysmo/__init__.py`](https://github.com/pysmo/pysmo/blob/master/pysmo/__init__.py)
  file.
- Unlike types and classes, no additional edits to the documentation source files are
  not necessary for the docstrings to be included in pysmo's documentation.


### Tools

Tools is a place where we group topical functions together (e.g. for things like signal
processing). It also may serve as a place for "anything else".

- Each tool should be it's own module, that can be imported as `pysmo.tools.<toolname>`.
  Therefore, tools that exist in a single file don't need a `__init__.py` file, and ones
  that exist in their own directory need an `__init__.py` file in that directory.
- Each tool's documentation should also be entirely within the module as docstrings.
- A markdown file needs to be added to
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
