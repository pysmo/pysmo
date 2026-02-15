---
tags:
  - Development
---
# Development

A central feature of pysmo is that any code using pysmo is easily reusable.
This means that code you write with pysmo could potentially become part of
pysmo itself. Whether you're maintaining your own fork or contributing back to
pysmo, it's important to understand the code organisation and repository
structure.

## Getting started

Begin developing pysmo by exploring the
[source code](https://github.com/pysmo/pysmo/tree/HEAD/src/pysmo) to
familiarise yourself with the code organisation.

### Docstrings as documentation

Much of the information about how pysmo is organised lives in the docstrings
of the source code itself — particularly in the `__init__.py` files of each
module. These docstrings describe the purpose and scope of each module and are
also rendered in the [API reference][pysmo] section of this documentation. When
adding new features, make sure to keep the relevant docstrings up to date.

### Project layout

The repository root folder contains a relatively simple layout. The four most
important items are:

1. `src`: this directory contains the pysmo source code.
2. `docs`: anything to do with documentation happens here.
3. `tests`: we use this directory to hold unit tests.
4. `Makefile`: most things can be managed with this makefile.
