---
icon: lucide/copy-plus
tags:
  - Development
---

# Contributing

## Ways to contribute

Not all of these involve writing code:

- **Questions.** Asking when something is unclear points at documentation that
    needs work. pysmo is developed in the open, so ask on GitHub, as an
    [issue](https://github.com/pysmo/pysmo/issues) or a
    [discussion](https://github.com/pysmo/pysmo/discussions). Answering other
    people's questions helps just as much.
- **Bug reports.** Open an [issue](https://github.com/pysmo/pysmo/issues), or
    add to an existing one. A failing test that reproduces the bug is ideal.
- **Code.** A useful function, a new type, or a tool built on pysmo can all be
    contributed. [Code standards](standards.md) covers what is expected.

## What a contribution contains

Well-written code, tests that cover it, and docstrings on anything public.
Because the documentation is generated from docstrings, a contribution is often
just two files: the implementation and its test.

## Submitting a pull request

Set up a checkout as described in [Setting up](environment.md), then work on a
branch:

```bash
git checkout -b my-feature
```

Before opening the pull request:

- Run `make format`, then `make lint` and `make tests`. All three must pass.
- [Rebase](https://git-scm.com/docs/git-rebase) onto the current `master` and
    squash the branch into one well-described commit, so the history carries no
    "fix typo" steps. Commit messages follow
    [conventional commits](https://www.conventionalcommits.org); the changelog
    is generated from them.

Opening the pull request triggers two automated checks:

- The test suite runs in clean environments on the supported Python versions. A
    pass locally but a failure here usually means a dependency is missing from
    `pyproject.toml`.
- The documentation is built. Follow the link on the pull request to check how
    it renders.

A maintainer then reviews the change.

## Contributors

pysmo is built by
[its contributors](https://github.com/pysmo/pysmo/graphs/contributors). Early
work on the project came from Omkar Ranadive, Helio Tejedor, Xiaoting Lou, and
Lay Kuan Loh.
