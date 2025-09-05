# Development Environment

## Git repository

We use [GitHub](https://github.com) for the development of pysmo. If you have
never used git and/or GitHub we recommend you first have a look at their
[documentation](https://docs.github.com/en/get-started). You can clone the pysmo
repository two different ways:

1. Clone the psymo repository directly to your desktop.
2. Fork the repository on GitHub, and then clone it to your desktop (recommended
   if you plan on submitting your changes to be included in pysmo).

### Clone directly

If you want to get started quickly, simply clone the pysmo git repository directly:

```bash
$ git clone https://github.com/pysmo/pysmo.github
Cloning into 'pysmo'...
$ cd pysmo
```

That's it! Now skip ahead to [project layout](#project-layout).

### Create your own fork

Creating your own [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
allows you to push your changes back to your fork on GitHub, which in turn makes
submitting a [pull request](https://docs.github.com/en/pull-requests)
straightforward. Once you forked pysmo, you can clone _your_ repository to your desktop:

```bash
$ git clone git@github.com:<github-username>/pysmo.git
Cloning into 'pysmo'...
$ cd pysmo
```

!!! note
    We used
    [ssh](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
    to clone the repository this time round. With an _ssh-agent_ running, this
    will save you from having to constantly enter your credentials when pushing
    changes back to GitHub.

In order to pull in changes in the upstream pysmo repository, we suggest adding
it as an additional remote:

```bash
git remote add upstream https://github.com/pysmo/pysmo.git
```

## Project layout

Inside the pysmo folder you will find a relatively simple layout. The four most important
items are:

1. `pysmo`: this directory is for the pysmo source code. There are `README.md`
  files in all relevant sub-directories here to help you find your way around.
2. `docs`: anything to do with documentation happens here.
3. `tests`: we use this directory to hold unit tests.
4. `Makefile`: Most things can be managed with this makefile.

!!! tip
    The psymo repository also contains files to create a
    [development container](https://containers.dev/), which performs the necessary
    setup tasks (all the steps below) for you automatically.

## Requirements

### Setting up Windows

To set up the development environment on Windows a few additional steps may be
needed:

* Install [Chocolatey](https://chocolatey.org/install#individual), a package manager
  for Windows which greatly simplifies installing additional dependencies
  correctly.
* Once Chocolatey is installed, run the following commands (as administrator)
  using either PowerShell or the Command Prompt to install the dependencies:

  ```powershell
  PS > choco install make
  PS > choco install awk
  ```

### uv

In order to develop pysmo in a consistent and isolated environment we use
[uv](https://docs.astral.sh/uv/). Uv creates a Python virtual environment and
manages the Python packages that are installed in that environment. This allows
developing and testing while also having the stable version of pysmo installed
at the same time.

!!! note
    uv can also be used to install Python itself.

## Makefile

Pysmo provides a `Makefile` that helps with common tasks. Running the `make` command
without arguments (or with `help`) will list available commands:

```bash
$ make help

This makefile executes mostly uv commands. To view all uv commands available
run 'uv help'.

AVAILABLE COMMANDS
  build                Build distribution.
  check-uv             Check if uv is installed.
  clean                Remove existing builds.
  docs                 Build html docs.
...
```

To get you started run

```bash
make sync
```

in a shell. This will first create a Python virtual environment for development
of pysmo (unless the environment already already exists), then install pysmo
and its dependencies.
