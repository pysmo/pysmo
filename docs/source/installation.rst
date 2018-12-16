============
Installation
============

Install pysmo with pip
----------------------

Simple installation in a users home directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest way to install Pysmo and all dependencies not already present
is via the `pip` command::

   $ pip install --user pysmo

This installs pysmo a users home directory. Similarly, to upgrade pysmo with `pip` run::

   $ pip install --user pysmo -U

.. caution:: We do not recommend running these commands as root or with sudo. While it may be
   tempting to install python packages system wide via pip, it is generally considered to be a
   bad idea. Installing them this way could interfere with the system in unpredictable, even
   harmful ways!



Installation inside a virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Experienced users already familiar with `Python virtualenv <https://virtualenv.pypa.io/en/latest/>`_ may
want to install pysmo in its own isolated virtual environment.  Much like the above method, this ensures
the system python remains isolated from packages installed via ``pip``. Additionally different versions
of pysmo can be installed alongside eachother (for example the currently stable and development versions).


Virtualenvwrapper
"""""""""""""""""

`Virtualenvwrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`_ is a convenient tool for
creating and managing virtual environments. It is frequently available via the package manager in
Linux distributions, but can also conveniently be installed with pip::

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

Once inside the virtual environment, pysmo can be installed and updated using pip without the ``--user`` flag::

   (testenv) $ pip install pysmo


.. note:: To end a session and use the system python run ``deactivate`` in your shell.


Conda
"""""

For anaconda users, we recommend creating a virtual environment with `conda`. For example,
to create a python-3.6 virtual environment::

   $ conda create -n pysmo python=3.6

Then enter the environment and install pysmo::

   $ conda activate pysmo
   $ pip install pysmo

Exit the pysmo virtual environment and switch back to the default anaconda installation::

   $ conda deactivate


Installation from GitHub
------------------------

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
