# Contributing

Thank you for considering contributing to pysmo. We welcome your contribution! To make
the process as seamless as possible, please read through this guide carefully.


## What are Contributions?

Broadly speaking, contributions fall into the following categories:

- *Questions*: the easiest way to contribute to pysmo is ask for help if something is
  unclear or you get stuck. Questions provide important feedback that helps us determine
  what parts of pysmo might need attention, so we are always keen to help. Development
  of pysmo happens publicly on [GitHub](https://github.com/pysmo/pysmo), and we kindly
  request that you ask your questions there too. You may either create a new
  [issue](https://github.com/pysmo/pysmo/issues) or start a
  [discussion](https://github.com/pysmo/pysmo/discussions). Please also feel free to
  answer any questions (including your own, should you figure it out!) to help out other
  users.
- *Bug reports*: if something needs fixing in psymo we definitely want to hear about it!
  Please create a new [issue](https://github.com/pysmo/pysmo/issues), or add relevant
  information to an issue if one already exists for the bug you found. Bonus points if
  you also provide a patch that fixes the bug!
- *Enhancements*: we reckon that if you are able to use pysmo, you are also able to write
  code that can become part of pysmo. These can be things such as useful functions, new
  pysmo types, or a cool example you would like to show off in the pysmo gallery.

Contributing towards making pysmo better does not necessarily mean you need to submit
code for inclusion in pysmo. However, if you do want to submit code, we ask that you read
the information and follow steps outlined in the remaining sections on this page.


## Development Workflow

As mentioned in the [previous chapter](project:developing.md#git-repository),
development of pysmo happens on [GitHub](https://github.com). Therefore, code submitted
via a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)
has a much greater chance to be included in pysmo than e.g. sending a patch to us via
email.

Typically you would first
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) pysmo and
configure git to sync your fork with the upstream repository. Then you create a new
feature branch where you add your code:

```bash
$ git checkout -b my_cool_feature
```

This feature branch is what you will also use to submit a pull request to pysmo when you
are finished implementing your changes. Before submitting a pull request, please make
sure you did the following:

  - Write code that adheres to the [PEP 8](https://peps.python.org/pep-0008/) style guide.
  - Include unit tests with your submission. If you need help with that, feel free to
    contact us.
  - Run a code linter on your code and verify the unit tests all still pass. Essentially
    this simply means [`make tests`{l=bash}](<project:developing.md#makefile>) still
    passes without errors.
  - In order to keep a clean git history, please
    [rebase](https://git-scm.com/docs/git-rebase) the pysmo master branch onto your
    feature branch, and squash all commits into a single, well documented commit.
    This avoids having commits such as "fix typo", or "undo changes" finding their way
    into the git log. Note that this should only be done before submitting the initial
    pull request.

Once a pull request is submitted the following happens:

  - The unit tests are executed automatically in clean Python environments via
    [GitHub Actions](https://docs.github.com/en/actions). Please verify all tests still
    pass. If the tests pass on your development machine but fail in the pull request, you
    may have e.g. forgotten to add a dependency to `pyproject.toml` that you happened to
    already have installed on your machine.
  - Similarly, a build of the documentation from the code as it exists in the pull
    request is also automatically triggered. Please follow the link that appears in the
    pull request on GitHub and verify the documentation is as expected.
  - We will then review your submission, and hopefully be able to include it in pysmo!


## What should be included

A good contribution should contain code that is well written and documented, as well as
provide meaningful test cases to ensure consistent and bug-free behaviour.

A lot of the pysmo documentation is generated from the docstrings within the `.py` files.
In many instances this means that a contribution may consist of only two files: the code
itself and an associated test file.

## Example contribution

In this subsection, we show an example contribution consisting of a simple function.


### Creating the function

We plan to submit a normalize function, which normalizes the seismogram with its absolute
max value and returns the new normalized seismogram. We first create a new feature branch
in our git repository for the development process. It is common practice to chose a branch
name that is descriptive of the feature being implemented. Here we create and switch to
the new branch in a single step:

```bash
$ git checkout -b func-normalize
```

Pysmo functions belong in the `pysmo/functions` folder, so we create the `normalize.py`
there with the following content:

```{literalinclude} ../../pysmo/functions/normalize.py
:language: python
```
```{note}
Notice that the code is making use of [type hinting](<project:not-so-fast.md>) and 
[pysmo types](<project:types.md>) covered in previous sections.
```

To ensure that this newly created function can be imported correctly, we add add it to
the `__init__.py`{l=bash} file in the `pysmo/functions` folder. This is what the
`__init__.py`{l=bash} file looks like after adding the normalize function to it:

```{literalinclude} ../../pysmo/functions/__init__.py
:language: python
```


### Creating a unit test

We also need to create an associated test file to ensure that the function returns a
correct output. In most instances, it actually makes sense to write the test case first
([test-driven development](https://en.wikipedia.org/wiki/Test-driven_development)).

The tests in pysmo are in the `tests` folder, where we keep the structure identical to
the pysmo source in the `pysmo` folder. Hence we add the file
`tests/functions/test_normalize.py` with the following content:

```{literalinclude} ../../tests/functions/test_normalize.py
:language: python
```

```{important}
The filename may not be arbitrary here: it must begin with `test`!
```

Pysmo tests are written for, and executed with [pytest](<inv:pytest#index>). Test data
such as the `seismograms`{l=python} used in our example above are defined in the file
`tests/conftest.py`. These fixtures provide a consistent (disposable) context to run
tests with. Running

```bash
$ make tests
```

will run all tests in the `tests` folder. A single test may be executed by running

```bash
$ poetry run pytest tests/functions/test_normalize.py
```


### Pushing the code

When we are happy with our code (and all tests pass without errors), we are ready to push
our code to GitHub. It is always a good idea to run `git status` before doing anything
else with git. This allows e.g. adding files that should not be tracked by git to the
`.gitignore` file. The code can then be pushed to a new branch on GitHub
(the branch `func-normalize` only exists on our development machine) as follows: 

```bash
$ git add .
$ git commit
$ git push origin -u func-normalize
```

The new branch is now on GitHub, where we are offered the option to submit a pull request
via the UI.

```{hint}
There are git UIs that make git tasks a lot easier (even for experienced developers).
You may therefore consider using something like
[Lazygit](https://github.com/jesseduffield/lazygit) or
[GitKraken](https://www.gitkraken.com/).
```
