---
tags:
  - Development
---

# Development

This chapter is for working on pysmo itself: fixing a bug, adding a function or
a type, or maintaining a fork.

Code written against the pysmo types is reusable by design, so a function
written for one study can often become a pysmo contribution with little change.
The [Usage](../usage/index.md) chapter covers the style that makes this
possible. This chapter covers the repository and the workflow around it.

## Project layout

Four things in the repository root matter for development:

- `src/` holds the pysmo source code.
- `tests/` holds the test suite, mirroring the layout of `src/`.
- `docs/` holds everything behind [docs.pysmo.org](https://docs.pysmo.org).
- `Makefile` collects shortcuts for the common development tasks.

## Documentation lives in the source

Each module documents its purpose and scope in its `__init__.py` docstring, and
the [API reference][pysmo] is generated from those docstrings together with the
ones on individual functions and classes. There is no separate API document to
keep in step: editing the code and editing its reference documentation are the
same action. A change in behaviour is not finished until the docstring matches.
