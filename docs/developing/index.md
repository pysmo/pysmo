# Developing pysmo

A central feature of pysmo is that any code using pysmo is easily reusable.
Therefore, any time you use pysmo, you are potentially also writing code that
can potentially be considered as part of pysmo itself. If this leads to you
maintaining your own fork, or even contributing back to pysmo, it is important
to understand a few things about pysmo code and repository structure.

## `README.md` files

The first step when developing pysmo is probably to browse the
[source](https://github.com/pysmo/pysmo/tree/HEAD/pysmo) to get a feel for how
the code is organised and to read through the `README.md` files you find
throughout the source directory. You may also need to edit these `README.md`
files if you introduce major changes to the code.

## `__init__.py` files and API Reference

The `__init__.py` files are the entry points for pysmo, and they will most
likely need to be edited when introducing new features to pysmo.

Similarly, the API reference in the
[docs](https://github.com/pysmo/pysmo/tree/HEAD/docs) folder may need editing
to include the documentation of your code.

## Formatting and Style

### Code

Adhering to python conventions such as [PEP 8](https://peps.python.org/pep-0008/)
and linting code with e.g. [flake8](https://flake8.pycqa.org/en/latest/)
results in clean and easily readable code. Aside from using those kinds of
tools, we highly encourage writing
[self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code).
For example, instead of writing code to calculate velocity like this:

```python title="documented-code.py"
# Calculate the velocity v
def v(d: float, t: float) -> float:
  """Calculates the velocity from distance and time."""
  # distance is d
  # time is t
  return d / t
```

Use more meaningful variable (and function) names to write code that is easier
to read and less error prone:

```python title="self-documenting-code.py"
def velocity(distance: float, time: float) -> float:
  """Calculates the velocity from distance and time."""
  return distance / time
```

### Documentation

This documentation is built using [mkdocs](https://www.mkdocs.org/) using the
[material](https://squidfunk.github.io/mkdocs-material/) theme. Thus the main
documentation source files are written in
[Markdown](https://en.wikipedia.org/wiki/Markdown). The docstrings in the `.py`
files are included via the [mkdocstrings](https://mkdocstrings.github.io)
plugin. Please write the docstrings using the
[google](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
style.

## Testing

Testing may present a chicken and egg type of situation, where the reference test
data are calculated from the code that is being tested itself. While this does help
avoid future code changes from breaking things, there is no way to know if the
initial code is actually correct (e.g. free from logical errors). Ideally, test data
should therefore be calculated using external tools. Where this is not possible,
we suggest writing tests that involve creating figures (with [matplotlib][]) that
can be manually inspected to see if the output makes sense. These figures then become
the reference data that future test runs can use via the [pytest-mpl][] extension
automatically.
