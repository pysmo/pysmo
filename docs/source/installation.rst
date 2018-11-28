Installation
============

Python virtualenv
-----------------

We recommend installing pysmo in a `Python virtualenv <https://virtualenv.pypa.io/en/latest/>`_.
This ensures the system python remains isolated from packages installed via e.g. ``pip`` or ``easy_install``,
and allows a user to install pysmo with all it's dependencies in their home directory.

Virtualenvwrapper
~~~~~~~~~~~~~~~~~

`Virtualenvwrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`_ is a convenient tool
for creating and managing virtual environments. It is frequently available via
the package manager in Linux distributions, but can also conveniently be installed with pip::

   $ sudo pip install virtualenvwrapper

Virtualenvwrapper is a set of shell functions defined in a file that needs to be sourced in the
shell startup file (e.g. ``.bashrc``). Additionally the directories where the virtual environments
and projects live should be defined. For example::

   export WORKON_HOME=$HOME/.virtualenvs
   export PROJECT_HOME=$HOME/Devel
   source /usr/local/bin/virtualenvwrapper.sh

.. note::  Adjust the paths according to your environment!

After starting a new shell or updating your environment (e.g. ``source ~/.bashrc``) you can now
create a Python virtual environment (e.g. 'testenv') for pysmo::

   $ mkvirtualenv testenv

and activate it::

   $ workon testenv

.. note:: To end a session and use the system python run ``deactivate`` in your shell.


Install pysmo with pip
----------------------

The simplest way to install pysmo is with pip::

   (testenv)$ pip install pysmo

This will download and install pysmo, as well as all packages it depends on.


Install pysmo from GitHub
-------------------------

If you prefer to install pysmo from GitHub, e.g. because you want to run the latest development version::

   (testenv)$ git clone https://github.com/pysmo/pysmo.git
   (testenv)$ cd pysmo
   (testenv)$ python setup.py install

This will first ensure all dependencies are installed, then build and install pysmo. If you wish to
make changes to the pysmo code without having to reinstall it after every change, replace the last line with::

   (testenv)$ python setup.py develop


.. note::  Once you are done developing and want to actually install pysmo run::
   
   
   (testenv)$ python setup.py develop --uninstall
   (testenv)$ python setup.py install
