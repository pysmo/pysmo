# Contributing

Thank you for considering contributing to pysmo. We welcome your contribution! To make
the process as seamless as possible, please read through this guide carefully.

## Development Workflow

We use [GitHub](https://github.com) for the development of PySmo. We recommend users interested in contributing to become proficient at using Github. Refer to our [introductory guide](./developing.md#git-repository) on understanding the basics of Github and setting up the repository. 

Over here we demonstrate a few common Git commands which would be required to make a contribution. Once you have cloned the Git repository as demonstrated in the [introductory guide](./developing.md#git-repository), you can start making changes to the project. A good practice is to create a separate _branch_ for each new feature you intend to make. In brief, branches allow us to develop features, fix bugs, or safely experiment with new ideas in a contained area of the repository. You can read more on branches [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches). 

Every Github repository has a primary branch called _master_ or _main_. Normally, we never want to push changes directly to main/master branch to avoid issues in the production version. To create a new branch we can run the following command 
```bash
$ git branch new-branch
```
Here, new-branch is the branch name. A good practice is to name the branches according to the feature that you are adding (e.g. win-makefile, docs-contrib, and func-normalize).
You can look up all the branches which are present locally with the following command: 
```bash
$ git branch
    * master
    new-branch  
```
The * indicates that we are currently at the master branch. To switch to the branch named "new-branch" we can run the following command: 
```bash
$ git checkout new-branch
```
This process of creating a new branch and then switching to it can be combined together into a single command as follows: 
```bash
$ git checkout -b new-branch
```
After switching to the right branch, we can then make changes to the code. To push the code back to the repository, we can run the following commands: 
```bash
$ git add .
$ git commit -m "Your commit message" 
$ git push origin -u new-branch 
```
* `git add .*`{l=bash}: This command adds all the changes in the current directory and its subdirectories to the staging area. The dot (.) represents the current directory. It prepares the changes to be committed.

* `git commit -m "Your commit message"`{l=bash}: This command creates a new commit with the changes that were added to the staging area in the previous step. The -m flag is used to provide a commit message in quotes. The commit message should briefly describe the changes made in the commit, such as bug fixes, new features, or other modifications.

* `git push origin -u new-branch`{l=bash}: This command pushes the local branch's commits to the remote repository. It sends the commits to the remote repository specified by origin. The -u flag is used to set up tracking between the local branch and the remote branch. new-branch represents the name of the branch to which you are pushing the changes.

You can read more about branching over [here](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell). 

## What should be included

A good contribution should be complete in the sense that the code should be well-written, well-documented, and should have associated test files to test out the code. These practices ensure that the code is bug free and can be easily understood by other users and contributors. 


## Example contribution

TODO: show a complete example
