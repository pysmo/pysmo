# Contributing

Thank you for considering contributing to pysmo. We welcome your contribution! To make
the process as seamless as possible, please read through this guide carefully.

## What are Contributions?

Broadly speaking, contributions fall into the following categories:

- *Questions*: the easiest way to contribute to pysmo is ask for help if something is
  unclear or you get stuck. Questions provide important feedback that helps us determine
  what parts of pysmo might need attention, so we are always keen to help. Development
  of pysmo happens publicly on [GitHub](https://github.com/pysmo/pysmo), and we kindly
  request that you ask your questions there too. You may either create a new
  [issue](https://github.com/pysmo/pysmo/issues) or start a
  [discussion](https://github.com/pysmo/pysmo/discussions). Please also feel free to
  answer any questions (including your own, should you figure it out!) to help out other
  users.
- *Bug reports*: if something needs fixing in psymo we definitely want to hear about it!
  Please create a new [issue](https://github.com/pysmo/pysmo/issues), or add relevant
  information to an issue if one already exists for the bug you found. Bonus points if
  you also provide a patch that fixes the bug!
- *Enhancements*: we reckon that if you are able to use pysmo, you are also able to write
  code that can become part of pysmo. These can be things such as useful functions, new
  pysmo types, or a cool example you would like to show off in the pysmo gallery.

Contributing towards making pysmo better does not necessarily mean you need to submit
code for inclusion in pysmo. However, if you do want to submit code, we ask that you read
the information and follow steps outlined in the remaining sections on this page.

## Development Workflow

We use [GitHub](https://github.com) for the development of pysmo. We recommend users 
interested in contributing to become proficient at using Github. Refer to our 
[introductory guide](<project:developing.md#git-repository>) on understanding the basics
of Github and setting up the repository. 

Over here we demonstrate a few common Git commands which would be required to make a 
contribution. Once you have cloned the Git repository as demonstrated in the 
[introductory guide](<project:developing.md#git-repository>), you can start making changes
 to the project. A good practice is to create a separate _branch_ for each new feature you
 intend to make. In brief, branches allow us to develop features, fix bugs, or safely 
experiment with new ideas in a contained area of the repository. You can read more on 
branches [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches). 

Every Github repository has a primary branch called _master_ or _main_. Normally, you 
never want to push changes directly to main/master branch to avoid issues in the 
production version. To create a new branch you can run the following command 
```bash
$ git branch new-branch
```
Here, new-branch is the branch name. A good practice is to name the branches according to 
the feature that you are adding (e.g. win-makefile, docs-contrib, and func-normalize).
You can look up all the branches which are present locally with the following command: 
```bash
$ git branch
    * master
    new-branch  
```
The * indicates that we are currently at the master branch. To switch to the branch named 
"new-branch" you can run the following command: 
```bash
$ git checkout new-branch
```
This process of creating a new branch and then switching to it can be combined together 
into a single command as follows: 
```bash
$ git checkout -b new-branch
```
After switching to the right branch, you can then make changes to the code. To push the 
code back to the repository, you can run the following commands: 
```bash
$ git add .
$ git commit -m "Your commit message" 
$ git push origin -u new-branch 
```
* `git add .`{l=bash}: This command adds all the changes in the current directory and its 
subdirectories to the staging area. The dot (.) represents the current directory. It 
prepares the changes to be committed.

* `git commit -m "Your commit message"`{l=bash}: This command creates a new commit with 
the changes that were added to the staging area in the previous step. The -m flag is used 
to provide a commit message in quotes. The commit message should briefly describe the 
changes made in the commit, such as bug fixes, new features, or other modifications.

* `git push origin -u new-branch`{l=bash}: This command pushes the local branch's commits 
to the remote repository. It sends the commits to the remote repository specified by 
origin. The -u flag is used to set up tracking between the local branch and the remote 
branch. new-branch represents the name of the branch to which you are pushing the changes.

You can read more about branching over 
[here](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell). 

The code can now be viewed by all developers of the repository. Once you are done 
developing, testing, and pushing your code to your specified branch, you can create a pull
 request to let others know about the changes that you have pushed to the branch. Once the 
 changes are reviewed, the pull request can be merged with the main branch. This practice 
 of creating a separate branch for development and then merging the changes through a pull 
 request after they are reviewed by others ensures that the main/master branch remains bug
 free. You can read more on creating pull requests over [here.](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)

## What should be included

A good contribution should be complete in the sense that the code should be well-written, 
well-documented, and should have associated test files to test out the code. These 
practices ensure that the code is bug free and can be easily understood by other users and
contributors. 


## Example contribution

In this subsection, we will be showing an example of making a contribution by creating an 
actual function, then writing a test file to test that function, and then finally pushing 
the code to Github. 

### Creating a function 
For this example, you will be creating a normalize function which normalizes the 
seismogram with its absolute max value and returns the new normalized seismogram. To get 
started, first create a new branch to isolate the development process. The branch name 
should be descriptive of the feature which you are implementing, so you can name it as 
**func-normalize** as it describes the task concisely. You can create and switch to this 
branch as follows: 

```bash
$ git checkout -b func-normalize
```

All our functions are present in ./pysmo/functions folder. To get started, create a new 
normalize.py under ./pysmo/functions folder. The function can then be written as follows: 
```{literalinclude} ../../pysmo/functions/normalize.py
:language: python
```
```{note}
Notice that the code is making use of [Type Hinting](<project:not-so-fast.md>) and 
[pysmo types](<project:types.md>) explained in the previous sections. 
```
To ensure that this newly created function can be accessed correctly, you also need to add
 it to the `__init__.py`{l=bash} file under the ./pysmo/functions folder. This is what 
the `__init__.py`{l=bash} file would look like after adding the normalize function to it. 
```{literalinclude} ../../pysmo/functions/__init__.py
:language: python
```

### Creating a test file
Now that you have created the normalize function, you also need to create an associated 
test file to ensure that the function is giving correct output. The test files for 
functions are placed under ./tests/functions folder and labeled as test_func_name.py. 
Therefore, you can create a new test file under this folder called test_normalize.py for 
the normalize function. All the tests are executed using 
[PyTest](https://docs.pytest.org/en/7.4.x/getting-started.html). As the normalize function
 is dividing all values by its absolute max value, no value in the returned seismogram 
object should be greater than 1. Hence, the test_normalize.py can include this check to 
ensure correctness of the function. It can be written as follows: 
```{literalinclude} ../../tests/functions/test_normalize.py
:language: python
```

You can then run the tests by typing `make tests`{l=bash} in the terminal. All test files 
will be executed using PyTest including the new test file which you just created i.e. 
test_normalize.py. If all tests pass without any errors, then you are now ready to push 
the code to Github. 

### Pushing the code
The code can be pushed to a new branch called func-normalize as follows: 
```bash
$ git add .
$ git commit -m "Your commit message" 
$ git push origin -u func-normalize
```
Now, the code should be visible in a separate branch called func-normalize on Github and 
it can be viewed by all developers of the project. Once you are satisfied with the changes
 you have made, you can create a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) so that the 
other developers can review the changes and potentially merge it with the main/master branch.  
