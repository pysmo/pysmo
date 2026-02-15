---
icon: lucide/copy-plus
tags:
  - Development
---

# Contributing

Thank you for considering contributing to pysmo. We welcome your contribution!
To make the process as seamless as possible, please read through this guide
carefully.

## Ways to contribute

There are several ways to contribute, and not all of them involve writing code:

- *Questions*: asking for help when something is unclear or you get stuck is
  one of the easiest ways to contribute. Questions help us identify areas that
  need attention. Since pysmo development happens publicly on
  [GitHub](https://github.com/pysmo/pysmo), we ask that you post questions
  there too — either as a new
  [issue](https://github.com/pysmo/pysmo/issues) or a
  [discussion](https://github.com/pysmo/pysmo/discussions). Feel free to
  answer questions from other users as well (including your own, should you
  figure it out!).
- *Bug reports*: if something needs fixing, we want to hear about it! Please
  create a new [issue](https://github.com/pysmo/pysmo/issues), or add
  information to an existing one if the bug has already been reported. Bonus
  points if you also provide a patch that fixes it!
- *Enhancements*: if you can use pysmo, you can also write code that becomes
  part of it — whether that is a useful function, a new pysmo type, or a tool
  you built using pysmo.

If you do want to submit code for inclusion in pysmo, please follow the steps
outlined below.

## What should be included?

A good contribution contains well-written, documented code along with
meaningful tests to ensure consistent, bug-free behaviour.

Since much of the pysmo documentation is generated from docstrings in the
source code, a contribution may often consist of just two files: the code
itself and an associated test file.

## Submitting code

As described in [Environment setup](./environment.md#git-repository), pysmo
development happens on [GitHub](https://github.com). Code submitted via
[pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)
has a much greater chance of being included than patches sent via email.

The typical workflow is to
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) pysmo,
configure git to sync your fork with the upstream repository, and then create
a feature branch for your changes:

```bash
git checkout -b my_cool_feature
```

Before submitting a pull request from your feature branch, please make sure
you have done the following:

- Write code that adheres to the [PEP 8](https://peps.python.org/pep-0008/)
  style guide.
- Include unit tests with your submission. If you need help with that, feel
  free to contact us.
- Run a code linter and verify that all unit tests pass. The command
  [`make tests`](./environment.md#makefile) should complete without errors.
- To keep a clean git history, please
  [rebase](https://git-scm.com/docs/git-rebase) the pysmo master branch onto
  your feature branch and squash your commits into a single, well-documented
  commit. This avoids entries like "fix typo" or "undo changes" in the git
  log. Do this before submitting your initial pull request.

Once a pull request is submitted:

- Unit tests run automatically in clean Python environments via
  [GitHub Actions](https://docs.github.com/en/actions). Please verify that
  all tests pass. If tests pass locally but fail in the pull request, you may
  have forgotten to add a dependency to `pyproject.toml` that happened to
  already be installed on your machine.
- A documentation build is also triggered automatically. Follow the link that
  appears in the pull request on GitHub and verify the documentation looks as
  expected.
- We will then review your submission and hopefully be able to include it in
  pysmo!
