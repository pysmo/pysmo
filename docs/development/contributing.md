---
icon: lucide/copy-plus
tags:
  - Development
---

# Contributing

Thank you for considering contributing to pysmo. We welcome your contribution!
To make the process as seamless as possible, please read through this guide
carefully.

## What are contributions?

Broadly speaking, contributions fall into the following categories:

- *Questions*: the easiest way to contribute to pysmo is to ask for help if
  something is unclear or you get stuck. Questions provide important
  feedback that helps us determine what parts of pysmo might need attention,
  so we are always keen to help. Development of pysmo happens publicly on
  [GitHub](https://github.com/pysmo/pysmo), and we kindly request that you
  ask your questions there too. You may either create a new
  [issue](https://github.com/pysmo/pysmo/issues) or start a
  [discussion](https://github.com/pysmo/pysmo/discussions). Please also
  feel free to answer any questions (including your own, should you figure it
  out!) to help out other users.
- *Bug reports*: if something needs fixing in pysmo we definitely want to hear
  about it! Please create a new [issue](https://github.com/pysmo/pysmo/issues),
  or add relevant information to an issue if one already exists for the bug
  you found. Bonus points if you also provide a patch that fixes the bug!
- *Enhancements*: we reckon that if you are able to use pysmo, you are also
  able to write code that can become part of pysmo. These can be things such as
  useful functions, new pysmo types, or a cool tool that you made using pysmo.

Contributing towards making pysmo better does not require submitting code.
However, if you do want to submit code for inclusion in pysmo, please read the
information and follow the steps outlined in the remaining sections.

## Development workflow

As mentioned in the [previous chapter](./developing.md#git-repository),
pysmo development happens on [GitHub](https://github.com). Code submitted via
[pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)
has a much greater chance of being included in pysmo than alternative methods
like sending patches via email.

Typically you would first
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) pysmo and
configure git to sync your fork with the upstream repository. Then you create a new
feature branch where you add your code:

```bash
git checkout -b my_cool_feature
```

This feature branch is what you will use to submit a pull request to pysmo
when you have finished implementing your changes. Before submitting a pull
request, please ensure you have done the following:

- Write code that adheres to the [PEP 8](https://peps.python.org/pep-0008/)
  style guide.
- Include unit tests with your submission. If you need help with that, feel
  free to contact us.
- Run a code linter on your code and verify that unit tests still pass.
  The command [`make tests`](./developing.md#makefile) should pass without errors.
- To keep a clean git history, please
  [rebase](https://git-scm.com/docs/git-rebase) the pysmo master branch onto
  your feature branch, and squash all commits into a single, well-documented
  commit. This avoids commits such as "fix typo" or "undo changes" from
  appearing in the git log. Do this before submitting your initial pull request.

Once a pull request is submitted the following happens:

- The unit tests are executed automatically in clean Python environments via
    [GitHub Actions](https://docs.github.com/en/actions). Please verify all
    tests still pass. If the tests pass on your development machine but fail in
    the pull request, you may have e.g. forgotten to add a dependency to
    `pyproject.toml` that you happened to already have installed on your
    machine.
- Similarly, a build of the documentation from the code as it exists in the
  pull request is also automatically triggered. Please follow the link that
  appears in the pull request on GitHub and verify the documentation is as
  expected.
- We will then review your submission, and hopefully be able to include it in
  pysmo!

## What should be included

A good contribution should contain code that is well written and documented, as
well as provide meaningful test cases to ensure consistent and bug-free
behaviour.

A lot of the pysmo documentation is generated from the docstrings within the
`.py` files. In many instances this means that a contribution may consist of
only two files: the code itself and an associated test file.
