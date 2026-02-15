---
icon: lucide/monitor-cog
tags:
  - Development
---

# Environment setup

## Git repository

We use [GitHub](https://github.com) for pysmo development. If you're new to
git and/or GitHub, we recommend reviewing their
[documentation](https://docs.github.com/en/get-started). There are two ways
to get a local copy of the repository:

1. Clone the pysmo repository directly.
2. Fork the repository on GitHub first, then clone your fork (recommended if
   you plan on contributing changes back to pysmo).

### Clone directly

To get started quickly, clone the pysmo repository directly:

```bash
$ git clone https://github.com/pysmo/pysmo.git
Cloning into 'pysmo'...
$ cd pysmo
```

That's it! Now skip ahead to [Requirements](#requirements).

### Create your own fork

Creating your own
[fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) lets
you push changes to GitHub under your own account, making it straightforward
to submit a [pull request](https://docs.github.com/en/pull-requests). Once
you have forked pysmo, clone _your_ repository:

```bash
$ git clone git@github.com:<github-username>/pysmo.git
Cloning into 'pysmo'...
$ cd pysmo
```

!!! note
    We used
    [SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
    to clone the repository here. With an _ssh-agent_ running, this saves you
    from having to enter your credentials every time you push to GitHub.

To pull in future changes from the upstream pysmo repository, add it as an
additional remote:

```bash
git remote add upstream https://github.com/pysmo/pysmo.git
```

## Requirements

### Setting up Windows

Setting up the development environment on Windows may require a few additional
steps:

* Install [Chocolatey](https://chocolatey.org/install#individual), a package
  manager for Windows that simplifies installing dependencies.
* Once Chocolatey is installed, run the following commands as administrator
  (PowerShell or Command Prompt):

  ```powershell
  PS > choco install make
  PS > choco install awk
  ```

### uv

We use [uv](https://docs.astral.sh/uv/) to manage a consistent, isolated
development environment. Uv creates a Python virtual environment and handles
package installation, so you can develop and test pysmo without affecting any
system-wide Python installation.

!!! note
    uv can also be used to install Python itself.

## Makefile

Pysmo provides a `Makefile` for common development tasks. Running `make`
without arguments (or with `help`) lists the available commands:

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

To get started, run:

```bash
$ make sync
...
```

This creates a Python virtual environment for pysmo development (if one does
not already exist) and installs pysmo along with all its dependencies.
