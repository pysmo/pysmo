=========================
Installation and Upgrades
=========================

Requirements
------------

Python
~~~~~~
Pysmo is built on top of `standard Python <https://www.python.org/>`_ and uses several extra Python libraries as well. We develop and test pysmo on Python versions 3.6 and newer. Pysmo may run on older versions too, but we strongly suggest upgrading Python should you be running an older version (not just for pysmo!).

Compilers
~~~~~~~~~
C
^
While pysmo itself does not use C, some of the Python libraries it uses potentially require a C compiler during installation. This may vary depending on computer platform, or Python version/distribution used.

Operating System
~~~~~~~~~~~~~~~~
Pysmo is designed to run on UNIX like systems (e.g. Mac OSX and Linux). Installation on Windows is probably possible (since Python can be installed on almost any platform), though untested.

Installing Pysmo
-----------------
pip - Python package installer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pysmo is available as a package from the `Python Package Index <https://pypi.org/>`_. This means it can be easily installed with the ``pip`` command (available by default since Python version 3.4).

.. caution:: It is possible to have multiple versions of Python installed on a computer. If this is the case, then there will also be multiple versions of the ``pip`` command. It is therefore important to use the ``pip`` command belonging to the Python version you intend to use for pysmo! Running ``pip --version`` will show you which Python version it belongs to.

.. note:: On some systems Python 2 and Python 3 are installed alongside eachother. Typically there is a ``pip`` command belonging to Python 2 and a ``pip3`` command belonging to Python 3.

conda users
~~~~~~~~~~~
If you are using conda to manage Python packages, we recommend installing pysmo dependencies with ``conda`` before installing pysmo with ``pip``. To do so issue this command::

   $ conda install scipy numpy matplotlib pyyaml pyproj

.. note:: Similarly, if you are using a package manager on Linux, or something like brew or macports on OSX, you may want to install these dependencies (if available) via those mechanisms instead of ``pip``.


Installing pysmo with pip
~~~~~~~~~~~~~~~~~~~~~~~~~~
To install the latest stable version of pysmo and all dependencies not already installed, simply issue this command::

   $ pip install pysmo

.. caution:: Unless you know what you are doing, we recommend to *not* install pysmo with administrative priveliges (i.e. using sudo or the root account). If the above command fails due to insuffienct rights, run the same command with the ``--user`` flag::

   $ pip install --user pysmo

If you wish to install the latest developement version of pysmo *instead* of the stable release::

   $ pip install git+https://github.com/pysmo/pysmo

.. note:: It is possible to install the stable release alongside the development version. Please read :ref:`Developing pysmo` for instructions.

Example Data
~~~~~~~~~~~~
Get the repository `data-example <https://github.com/pysmo/data-example>`_ from Github. There is some example code inside `data-example/example_pkl_files` that will be needed for later demonstrations.

Upgrading pysmo
----------------
Upgrading pysmo with ``pip`` is done with the same command used to install, with the addition of the ``-U`` flag::

   $ pip install -U pysmo

.. note:: If you used the ``--user`` flag during installation you also need to use it while upgrading

Uninstalling pysmo
-------------------
To remove pysmo from your system with ``pip`` run this command::

   $ pip uninstall pysmo

.. note:: Unfortunately ``pip`` currently does not remove dependencies that were automatically installed. We suggest running ``pip list`` to see the installed packages, which can then also be removed using ``pip uninstall``
