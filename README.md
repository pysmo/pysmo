<h1 align="center">pysmo</h1>

<div align="center">
<a href="https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml" target="_blank">
<img src="https://github.com/pysmo/pysmo/actions/workflows/run-tests.yml/badge.svg" alt="Test Status">
</img></a>
<a href="https://github.com/pysmo/pysmo/actions/workflows/build.yml" target="_bank">
<img src= "https://github.com/pysmo/pysmo/actions/workflows/build.yml/badge.svg" alt="Build Status">
</img></a>
<a href="https://pysmo.readthedocs.io/en/latest/?badge=latest" target="_blank">
<img src="https://readthedocs.org/projects/pysmo/badge/?version=latest" alt="Documentation Status">
</img></a>
<a href="https://codecov.io/gh/pysmo/pysmo" target="_blank">
<img src="https://codecov.io/gh/pysmo/pysmo/branch/master/graph/badge.svg?token=ZsHTBN4rxF" alt="codecov">
</img></a>
<a href="https://pypi.org/project/pysmo/" target="_blank">
<img src="https://img.shields.io/pypi/v/pysmo" alt="PyPI">
</img></a></div>

<p align="center">
<em>Documentation:</em> <a href="https://docs.pysmo.org" target="_blank">https://docs.pysmo.org</a>
</p>
<p align="center">
<em>Source Code:</em> <a href="https://github.com/pysmo/pysmo" target="_blank">https://github.com/pysmo/pysmo</a>
</p>

---
The addition of type annotations to Python marked a significant step forward
in user experience (e.g. intelligent autocompletion in modern editors) and type
safety (by catching errors before code is executed). With types thus becoming
more meaningful, it is worth revisiting what a type should *mean* to a
seismologist.

Traditionally a lot of data are stored together (e.g. in a seismogram file of
some format containing a time series and its metadata), only for most of that
data to be ignored during processing. While it makes sense to *store* the data
together, it is better to split them up into far simpler types when writing
code for *processing*.

Pysmo offers simple data types for seismologists to write code with. Instead
of working with one big class containing all kinds of data, psymo uses
separate, narrowly defined protocol classes that are not tied to any particular
file format or existing class.

Code written with pysmo types is easy to understand and maintain. Most
importantly, it can often be reused in different projects, thus reducing the
duplication of effort.

Pysmo itself is designed to be modular and easy to expand without interfering
with the existing code base, making it straightforward to incorporate user
contributions.
