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

Pipenv
------
In order to develop pysmo in a consistent and isolated environment we use `pipenv <https://pipenv.readthedocs.io/en/latest/>`_. Pipenv creates a Python virtual environment and manages the Python packages that are installed in that environment. This allows developing and testing while also having the stable version of pysmo installed at the same time. If pipenv isn't already available on your system you can install it with pip::

   $ pip install pipenv

Next use pipenv to create a new Python virtual environment and install all packages needed for running and developing pysmo::

   $ pipenv install --dev

Once this command has finished (it may take a while to complete), you can spawn a shell that uses this new Python virtual environment by running ``pipenv shell`` or execute commands that run in the environment with ``pipenv run`` For example, to build and install pysmo for development you would run::

   $ pipenv run python setup.py develop

.. caution:: Please note that pipenv only creates a virtual environment for Python - it is not comparable to a virtual machine and does not offer the same separation!

.. note:: For convenience we put a lot of these commands in a ``Makefile`` for you to use.

At this point you can use the stable version of pysmo in your regular shell, and if you spawn one with ``pipenv shell`` (from within the ``pysmo`` repository you cloned earlier) you are using the development version!

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
~~~~~~~~~~~~~~~~~

To run all the tests in one go from the root directory of the pysmo repository::

   $ pipenv run py.test -v tests

or::

   $ make test

Individual test scripts can also be specified::

   $ pipenv run py.test -v tests/<test_script>.py
