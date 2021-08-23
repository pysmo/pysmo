=================
Developing pysmo
=================

Github
------
We use Github for the development of pysmo. Github is easiest to use with authentication using SSH keys. Please refer to the `Github documentation <https://help.github.com/en/articles/connecting-to-github-with-ssh>`_ for setup instructions on your platform.

Once your account is properly set up you can copy the pysmo repository to the your workstation with the ``git clone`` command::

   $ git clone git@github.com:pysmo/pysmo.git

You can now navigate to the ``pysmo`` directory and explore the files::

   $ cd pysmo
   $ ls
   build docs ...

.. note:: If you are not a member of the `pysmo group <https://github.com/pysmo>`_ on Github you will have to first fork the pysmo repository (from the GUI on Github).

Poetry
------
In order to develop pysmo in a consistent and isolated environment we use `Poetry <https://python-poetry.org/>`_. Poetry creates a Python virtual environment and manages the Python packages that are installed in that environment. This allows developing and testing while also having the stable version of pysmo installed at the same time. Please see the `Poetry documentation <https://python-poetry.org/docs>`_ for installation and basic usage instructions. Once Poetry is installed its commands can be viewed by running::

  $ poetry --help

.. caution:: Please note that poetry only creates virtual environments for Python - these are not comparable to a virtual machine and do not offer the same separation!

.. note:: For convenience we wrap the most used poetry commands in a ``Makefile``.

Makefile
--------

Pysmo provides a ``Makefile`` to aid with setting up and using a development environment. To list the available make commands run::

  $ make help

The most commonly used ones will likely be::

  $ make install

to create a Python virtual environment for development of pysmo (unless it already exists), then install pysmo and its dependencies, ::

  $ make tests

to run the test scripts from the tests directory, and ::

  $ make shell

which starts a new new shell in the virtual environment. This shell uses the pysmo virtual Python environment instead of the default one. In other words, executing Python will use the development version of pysmo (i.e. the source files in the working directory).

.. note:: Within the virtual environment, any changes made to the the pysmo source files are used without having to re-issue ``make install``.

Git workflows
-------------
There are different ways to use and achieve the same result with git. The guidelines here are aimed at developers not yet familiar with how git is best used to work as a team with other people.

Please avoid committing changes to the master branch directly. Even for small changes it is good practice to create a branch, and then either merge the changes in this branch into the master branch directly or via a pull request on Github (preferred). It is also generally a good idea to push and pull changes frequently, so that the local working copy on a workstation does not diverge too far from the `origin`, which is the version on Github.

Create a new branch
^^^^^^^^^^^^^^^^^^^
To pull the latest master revision from Github and create and switch to a new branch on your local workstation in one step::

   $ git pull
   $ git checkout -b <newbranch>

Next make changes to the pysmo code. In order to get the changes into the branch, first stage them with ``git add`` and then commit them with ``git commit``::

   $ git add <MyChangedFile>
   $ git commit

.. note:: ``git status`` will not only show you the status of your branch, it will also provide you with useful hints.

The final step is to upload your changes to Github, where a pull request can be created in the GUI to have these changes merged into the master branch::

   $ git push --set-upstream origin

If you now longer need the working branch you can switch back to master and delete the working branch::

   $ git checkout master
   $ git branch -d <newbranch>


Use an existing branch
^^^^^^^^^^^^^^^^^^^^^^
When working on the same feature or bug as another developer, you will likely also be working on the same branch. As with most git operations, you first pull the latest changes to your workstation first. Then you switch to the branch you want to work on::

   $ git pull
   $ git checkout <existingbranch>

Just like with a new branch, you must first stage and then commit your changes::

   $ git add <MyChangedFile>
   $ git commit

Since the branch already exists on Github, the ``push`` command is a bit simpler::

   $ git push

Again you can delete the working branch if you don't need it anymore (and if you do, you can always check it out again)::

   $ git checkout master
   $ git branch -d <newbranch>


Unit testing
------------
Unit tests execute a piece of code (a unit) and compare the output of that execution with a known reference value. Hence if changes to the pysmo code accidentally break functionality, unit tests are able to detect these before they are commited to the master branch (or worse to a stable release!). The unit tests in pysmo use the `pytest framework <https://docs.pytest.org/en/latest/>`_. 


Running the Tests
^^^^^^^^^^^^^^^^^

To run all the tests in one go from the root directory of the pysmo repository::

   $ make test

Individual test scripts may also be specified::

	 $ poetry run py.test -mpl -v tests/<test_script>.py
