.. highlight:: bash

.. _Python Package Index: https://pypi.org/project/pysmo/
.. _Python: https://www.python.org/
.. _NumPy: https://numpy.org
.. _SciPy: https://scipy.org

Installing pysmo
================

Prerequisites
-------------
Pysmo is built on top of standard `Python`_ and uses some popular third party modules (e.g.
`NumPy`_, `SciPy`_). In order to benefit from modern Python features and up to date modules,
pysmo is developed on the latest stable Python versions. Automatic tests are done on
version 3.10 and newer.

Pysmo is available as a package from the `Python Package Index`_. This means it
can be easily installed using the ``pip`` module::

  $ python3 -m pip install pysmo

Pre-release versions of pysmo can be installed with the `--pre` flag::

  $ python3 -m pip install pysmo --pre

Finally, the latest development version of Pysmo can be installed directly from Github by
running::

   $ python -m pip install git+https://github.com/pysmo/pysmo

.. note:: It is possible to install the stable release alongside the development
   version. Please read :ref:`developing:developing pysmo` for instructions.

Upgrading
---------
Upgrades to pysmo are also performed with the ``pip`` command::

   $ python3 -m pip install -U pysmo

Uninstalling
------------
To remove Pysmo from the system with::

   $ python3 -m pip uninstall pysmo

.. note:: Unfortunately ``pip`` currently does not remove dependencies that were
   automatically installed. We suggest running ``pip list`` to see the installed
   packages, which can then also be removed using ``pip uninstall``
