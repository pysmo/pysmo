---
icon: lucide/paintbrush
tags:
  - Development
---

# Code standards

Contributed code is held to the same standards as the code already in pysmo:
readable, typed, documented, and tested. `make lint` and `make tests` check most
of this automatically.

## Code style

pysmo follows [PEP 8](https://peps.python.org/pep-0008/), enforced by
[ruff](https://docs.astral.sh/ruff/). `make format` applies the formatting and
import order; `make lint` reports whatever is left. Beyond formatting:

- **British English** in comments, docstrings, and messages: `normalise`,
    `colour`, `centre`. Identifiers are the exception, where American spelling
    is the more common convention in Python code: the function is
    [`normalize`][pysmo.functions.normalize], not `normalise`.
- **Type annotations** on every function. mypy runs with
    `disallow_untyped_defs`, so an unannotated definition is an error.
- **Modern syntax** for the supported Python versions: `list[str]`, `X | None`,
    and PEP 695 generics.

Prefer a clear name over a comment explaining an unclear one. Rather than:

```python title="cryptic.py"
def v(d: float, t: float) -> float:
    """Calculate velocity from distance and time."""
    # d is distance, t is time
    return d / t
```

write:

```python title="clear.py"
def velocity(distance: float, time: float) -> float:
    """Calculate velocity from distance and time."""
    return distance / time
```

## Docstrings

pysmo uses
[Google-style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html)
docstrings. `mkdocstrings` renders them into the [API reference][pysmo], so a
docstring is user-facing documentation rather than an internal note. Omit types
from `Args` and `Returns` where the annotation already gives them.

An `Examples` section is executed as a test, through
[Sybil](https://sybil.readthedocs.io), so every example has to run and produce
the output shown.

## Tests

Every contribution needs tests, and the suite runs with `make tests`.

Scientific code has a chicken-and-egg problem: the reference values used to
check a result are often produced by the same code under test. Regression tests
of that kind catch later changes in behaviour but cannot confirm the original
result is correct. Where an independent tool can produce the reference values,
use it.

Where no independent reference exists, a test can plot its result with
[matplotlib][] for inspection by eye. Once confirmed, the figure becomes a
baseline that [pytest-mpl][] compares against on later runs.
