---
tags:
  - Development
---
# Developing pysmo

A central feature of pysmo is that any code using pysmo is easily reusable.
This means that code you write with pysmo could potentially become part of pysmo
itself. Whether you're maintaining your own fork or contributing back to pysmo,
it's important to understand the code organization and repository structure.

## `README.md` files

Begin developing pysmo by exploring the
[source code](https://github.com/pysmo/pysmo/tree/HEAD/pysmo) to familiarize yourself
with the code organization. Read through the `README.md` files you find
throughout the source directory to understand module purposes. If you introduce
major changes to the code, be sure to update the relevant `README.md` files.

## `__init__.py` files and API Reference

The `__init__.py` files are the entry points for pysmo modules. When adding new
features, you'll likely need to update these files to expose your code in the
public API. Additionally, update the [API reference](https://github.com/pysmo/pysmo/tree/HEAD/docs)
in the docs folder to document your code.

## Formatting and style

### Code

We recommend adhering to [PEP 8](https://peps.python.org/pep-0008/) and using
linters like [flake8](https://flake8.pycqa.org/en/latest/) to ensure clean,
readable code. Beyond these conventions, we highly encourage writing
[self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code)
with meaningful names that make the code's intent clear.

For example, avoid writing code with cryptic variable names like this:

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

This documentation is built using [zensical](https://zensical.dev/). The main
documentation source files are written in [Markdown](https://en.wikipedia.org/wiki/Markdown).
The docstrings in the `.py` files are included via the [mkdocstrings](https://mkdocstrings.github.io)
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
