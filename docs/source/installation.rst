Getting Started
===============

Requirements
------------

Python
~~~~~~
Pysmo is built on top of `standard Python <https://www.python.org/>`_ together with some popular
third party modules (e.g. `NumPy <https://numpy.org>`_, `SciPy <https://scipy.org>`_). In order
to make use of modern Python features and up to date modules, we develop Pysmo on the latest
stable Python versions and run automatic tests on version 3.9 and newer. Pysmo may run on older
versions of Python, but we strongly encourage against using it that way.

Compilers
~~~~~~~~~
While Pysmo itself does not use C, some of the Python libraries it uses potentially require a C
compiler during installation. This may vary depending on computer platform or Python
version/distribution used.

Operating System
~~~~~~~~~~~~~~~~
Pysmo is designed to run on UNIX like systems (e.g. Mac OSX and Linux). Installation on Windows
is probably possible (since Python can be installed on almost any platform), though untested.

Installing Pysmo
-----------------
Pysmo is available as a package from the `Python Package Index <https://pypi.org/>`_. This means it
can be easily installed with the ``pip`` command (available by default since Python version 3.4).

.. note:: It is possible to have multiple versions of Python installed on a single system, each
   with its own ``pip`` command. Running ``pip --version`` will show which Python version it belongs
   to.

System Python
~~~~~~~~~~~~~
Most modern UNIX like operating systems ship with some version of Python. If it is recent enough it
may be used to install Pysmo and its dependencies in the users home directory by running::

   $ pip install --user pysmo

.. caution:: We strongly advise **against** installing Pysmo with administrative priveliges (i.e.
   omitting the ``--user`` flag and using sudo or the root account to run ``pip``).

User Python
~~~~~~~~~~~
In cases where Python itself is installed for the current user (e.g. using downloads from
sources like `www.python.org <https://www.python.org>`_, `Anaconda <https://www.anaconda.com>`_,
or using tools like `pyenv <https://github.com/pyenv/pyenv>`_) the ``--user`` flag is not
required, and Pysmo can be installed with::

   $ pip install pysmo

If desired, the latest development version of Pysmo can be installed *instead* of the
stable release::

   $ pip install git+https://github.com/pysmo/pysmo

.. note:: It is possible to install the stable release alongside the development
   version. Please read :ref:`developing:developing pysmo` for instructions.

Upgrading Pysmo
----------------
Upgrades to Pysmo are also performed with the ``pip`` command::

   $ pip install -U pysmo

.. note:: If the ``--user`` flag was used during installation it also needs to be
   used for upgrades.

Uninstalling Pysmo
-------------------
To remove Pysmo from the system with ``pip``::

   $ pip uninstall pysmo

.. note:: Unfortunately ``pip`` currently does not remove dependencies that were
   automatically installed. We suggest running ``pip list`` to see the installed
   packages, which can then also be removed using ``pip uninstall``
