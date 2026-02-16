---
icon: lucide/paintbrush
tags:
  - Development
---
# Formatting and style

## Code

We recommend adhering to [PEP 8](https://peps.python.org/pep-0008/) and using
linters like [ruff](https://docs.astral.sh/ruff/linter/) to ensure clean,
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

Instead, use meaningful variable and function names to write code that is
easier to read and less error prone:

```python title="self-documenting-code.py"
def velocity(distance: float, time: float) -> float:
  """Calculates the velocity from distance and time."""
  return distance / time
```

## Documentation

This documentation is built using [zensical](https://zensical.dev/). The main
documentation source files are written in
[Markdown](https://en.wikipedia.org/wiki/Markdown), while API documentation is
generated from docstrings in the source code via the
[mkdocstrings](https://mkdocstrings.github.io) plugin. Please write docstrings
using the
[Google style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).
