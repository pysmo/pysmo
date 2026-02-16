# Changelog

All notable changes to the **pysmo** project will be documented in this file.

## [Unreleased]

### ⚙️ DevOps & Infrastructure

- Combine coverage results before uploading and add osx
- Add dependabot for gh actions
- Add gh-pages workflow
- Use poetry with mkdocs
- Replace deprecated test-results-action with codecov-action ([#238](https://github.com/pysmo/pysmo/issues/238))
- Use dynamic versioning

### 🐛 Bug Fixes

- Adjust tutorial to new naming in sac class
- Add event time to SacEvent ([#120](https://github.com/pysmo/pysmo/issues/120))
- Use paramspec (for now) on value_not_none decorator
- Importerror ([#136](https://github.com/pysmo/pysmo/issues/136))
- Move coverage combine out of tox for gh actions
- Need to clear cache after updating time window
- Ensure iccs seismogram lengths are always equal
- Add key to sorted call
- Index was out of bounds with --all
- Allow selecing index 0
- Correct type in sacstation.elevation setter

### 📚 Documentation

- Switch from sphinx to mkdocs ([#111](https://github.com/pysmo/pysmo/issues/111))
- Switch to google type docstrings. ([#112](https://github.com/pysmo/pysmo/issues/112))
- Update "not-so-fast" section
- Be a bit more specific in 'rules of the land'
- Add linting instructions to contribution section
- Add mkdocstrings-python
- Switch to jupyter lab, update packages
- Update tutorial
- Add BIB_FILE env variable
- Update mkdocs-bibtex
- Bump python version in build
- Add bib file
- Use relative paths for images and other pages
- Update noise example
- Add a small paragraph on how to use the documentation
- Switch to zensical
- Simpler tutorial
- Split usage into smaller sections
- Update development section
- Add FAQs
- Add more details to readme

### 🔍 Other Changes

- Bump version in pyproj.toml
- Modify build workflow to run on new tags
- Merge pull request #104 from pysmo/publish-action

Modify build workflow to run on new tags
- Issue #65: providing error message from IRIS service ([#105](https://github.com/pysmo/pysmo/issues/105))

When IRIS service responses with 4x or 5x error, _SacIO.from_iris raises a ValueError with the message description.

closes #65
- Noise tests ([#106](https://github.com/pysmo/pysmo/issues/106))

* Add unit tests for tools.noise
- Add a bit more testing ([#107](https://github.com/pysmo/pysmo/issues/107))

* add some tests and create _SacIO defaults when creating a new SAC object
- Rename _Sacio to SacIO and move it to pysmo/lib/io

* a bit of a code cleanup for sacio
* add azdist function to lib/functions.py
* update packages
- Merge pull request #108 from pysmo/cleanup-sacio

Rename _Sacio to SacIO and move it to pysmo/lib/io
- Use poetry to generate requirements.txt in readthedocs build
- Update deps
- Merge pull request #110 from pysmo/updates

Update deps
- Don't build singlehtml
- Add py.typed
- Small tweaks to test config

* move flake8 config to tox.ini
* define pytest test dir in pyproject.toml and adjust makefile
- Move SAC helper classes inside SAC class
- Merge pull request #113 from pysmo/nested-sac-classes

refactor: move SAC helper classes inside SAC class
- Merge pull request #114 from pysmo/fix-tutorial

fix: adjust tutorial to new naming in sac class
- Move functions into a single file
- Merge pull request #115 from pysmo/single-functions-file

refactor: move functions into a single file
- Rearrange test structure to match changes in src structure
- Merge pull request #116 from pysmo/func-tests

tests: rearrange test structure to match changes in src structure
- Merge pull request #117 from pysmo/methods

feat: add methods corresponding to functions to mini class
- Strip whitespaces and \x00 chars when reading sac files.
- Merge pull request #118 from pysmo/sacfix

Fix: strip whitespaces and \x00 chars when reading sac files.
- Merge pull request #119 from pysmo/type-event

feat: add Event type and MiniEvent class
- Fix typo in mini module documentation
- Rewrite sacio as (pydantic) dataclass
- Merge pull request #121 from pysmo/sacio-dataclass

refactor: rewrite sacio as (pydantic) dataclass
- Use pydantic dataclass for mini classes
- Merge pull request #122 from pysmo/mini-pydantic-dataclass

refactor: use pydantic dataclass for mini classes
- Re-organise test folders and fixtures.
- Merge pull request #123 from pysmo/better-tests

tests: re-organise test folders and fixtures.
- Change clone_to_miniseismogram function to classmethod clone in MiniSeismogram
- Merge pull request #124 from pysmo/mini-methods

refactor: change clone_to_miniseismogram function to classmethod
- Merge pull request #125 from pysmo/docs-not-so-fast

docs: update "not-so-fast" section
- Use attrs instead of pydantic
- Merge pull request #126 from pysmo/attrs

refactor: use attrs instead of pydantic
- Merge pull request #127 from pysmo/sacio_header_v7

feat: sacio.py can read SAC version 7 files
- Lint with ruff instead of flake8
- Merge pull request #128 from pysmo/ruff

test: lint with ruff instead of flake8
- Merge pull request #129 from pysmo/docs-rules

docs: be a bit more specific in 'rules of the land'
- Check tutorial notebook runs error free
- Merge pull request #130 from pysmo/test-tutorial

test: check tutorial notebook runs error free
- Merge pull request #131 from pysmo/ci-merge-coverage

ci: combine coverage results before uploading and add osx
- Merge pull request #132 from pysmo/fix-docorator-typing

fix: use paramspec (for now) on value_not_none decorator
- Fix typo in makefile help string
- Rename sacio jinja template file
- Switch to formatting with black
- Ignore black commit in git blame
- Merge pull request #133 from pysmo/black

Introduce Black to repository
- Merge pull request #134 from pysmo/sacio-check-required-on-read

feat: RuntimeError when trying to read invalid SAC file.
- Update packages
- Merge pull request #135 from pysmo/updates

chore: update packages
- Rename sampling_rate to delta.
- Merge pull request #137 from pysmo/fix-delta

refactor: rename sampling_rate to delta.
- **(deps)** Bump urllib3 from 2.0.4 to 2.0.6
- Merge pull request #139 from pysmo/dependabot/pip/urllib3-2.0.6

chore(deps): bump urllib3 from 2.0.4 to 2.0.6
- Add py312 to matrix
- Merge pull request #140 from pysmo/py312

chore: add py312 to matrix
- **(deps)** Bump pillow from 10.0.0 to 10.0.1
- Merge pull request #141 from pysmo/dependabot/pip/pillow-10.0.1

chore(deps): bump pillow from 10.0.0 to 10.0.1
- **(deps)** Bump urllib3 from 2.0.6 to 2.0.7
- Merge pull request #142 from pysmo/dependabot/pip/urllib3-2.0.7

chore(deps): bump urllib3 from 2.0.6 to 2.0.7
- Don't install pandoc, don't run post attach commands ([#143](https://github.com/pysmo/pysmo/issues/143))
- Update packages and run tox lint and report on py312
- Merge pull request #144 from pysmo/updates

chore: update packages and run tox lint and report on py312
- Cleanup CI config
- **(deps-dev)** Bump jupyter-server from 2.10.0 to 2.11.2
- Merge pull request #145 from pysmo/dependabot/pip/jupyter-server-2.11.2

chore(deps-dev): bump jupyter-server from 2.10.0 to 2.11.2
- **(deps-dev)** Bump jinja2 from 3.1.2 to 3.1.3
- Merge pull request #146 from pysmo/dependabot/pip/jinja2-3.1.3

chore(deps-dev): bump jinja2 from 3.1.2 to 3.1.3
- **(deps-dev)** Bump jupyter-lsp from 2.2.0 to 2.2.2
- Merge pull request #147 from pysmo/dependabot/pip/jupyter-lsp-2.2.2

chore(deps-dev): bump jupyter-lsp from 2.2.0 to 2.2.2
- **(deps-dev)** Bump notebook from 7.0.6 to 7.0.7
- Merge pull request #148 from pysmo/dependabot/pip/notebook-7.0.7

chore(deps-dev): bump notebook from 7.0.6 to 7.0.7
- **(deps-dev)** Bump jupyterlab from 4.0.8 to 4.0.11
- Merge pull request #149 from pysmo/dependabot/pip/jupyterlab-4.0.11

chore(deps-dev): bump jupyterlab from 4.0.8 to 4.0.11
- **(deps)** Bump pillow from 10.1.0 to 10.2.0
- Merge pull request #150 from pysmo/dependabot/pip/pillow-10.2.0

chore(deps): bump pillow from 10.1.0 to 10.2.0
- Update packages and format some code
- Merge pull request #151 from pysmo/updates

chore: update packages and format some code
- **(deps-dev)** Bump black from 24.2.0 to 24.3.0
- Merge pull request #152 from pysmo/dependabot/pip/black-24.3.0

chore(deps-dev): bump black from 24.2.0 to 24.3.0
- **(deps)** Bump pillow from 10.2.0 to 10.3.0
- Merge pull request #154 from pysmo/dependabot/pip/pillow-10.3.0

chore(deps): bump pillow from 10.2.0 to 10.3.0
- **(deps)** Bump actions/checkout from 3 to 4
- Merge pull request #158 from pysmo/dependabot/github_actions/actions/checkout-4

chore(deps): bump actions/checkout from 3 to 4
- **(deps)** Bump codecov/codecov-action from 3 to 4
- Merge pull request #159 from pysmo/dependabot/github_actions/codecov/codecov-action-4

chore(deps): bump codecov/codecov-action from 3 to 4
- **(deps)** Bump actions/setup-python from 4 to 5
- Merge pull request #156 from pysmo/dependabot/github_actions/actions/setup-python-5

chore(deps): bump actions/setup-python from 4 to 5
- **(deps)** Bump actions/upload-artifact from 3 to 4
- Merge pull request #155 from pysmo/dependabot/github_actions/actions/upload-artifact-4

chore(deps): bump actions/upload-artifact from 3 to 4
- **(deps)** Bump actions/download-artifact from 3 to 4
- Merge pull request #157 from pysmo/dependabot/github_actions/actions/download-artifact-4

chore(deps): bump actions/download-artifact from 3 to 4
- Update pytest to version 8 ([#160](https://github.com/pysmo/pysmo/issues/160))
- Update dependencies
- Merge pull request #161 from pysmo/updates

chore: update dependencies
- **(deps)** Add zlib to dev environment
- (feat) Add sac timestamps
- Merge pull request #163 from pysmo/timestamps

(feat) Add sac timestamps
- **(deps-dev)** Bump jinja2 from 3.1.3 to 3.1.4
- Merge pull request #164 from pysmo/dependabot/pip/jinja2-3.1.4

chore(deps-dev): bump jinja2 from 3.1.3 to 3.1.4
- ---
updated-dependencies:
- dependency-name: requests
  dependency-type: direct:production
...

Signed-off-by: dependabot[bot] <support@github.com>
- Merge pull request #165 from pysmo/dependabot/pip/requests-2.32.0

chore(deps): bump requests from 2.31.0 to 2.32.0
- **(deps)** Bump certifi from 2024.2.2 to 2024.7.4
- Merge pull request #168 from pysmo/dependabot/pip/certifi-2024.7.4

chore(deps): bump certifi from 2024.2.2 to 2024.7.4
- **(deps)** Bump urllib3 from 2.2.1 to 2.2.2
- Merge pull request #167 from pysmo/dependabot/pip/urllib3-2.2.2

chore(deps): bump urllib3 from 2.2.1 to 2.2.2
- **(deps-dev)** Bump tornado from 6.4 to 6.4.1
- Merge pull request #166 from pysmo/dependabot/pip/tornado-6.4.1

chore(deps-dev): bump tornado from 6.4 to 6.4.1
- Update deps
- Merge pull request #169 from pysmo/updates

chore: update deps
- Upload hidden files as artifacts for codecov ci step
- Merge pull request #170 from pysmo/upload-hidden-artifacts

chore: upload hidden files as artifacts for codecov ci step
- Add codecov token to workflow
- Merge pull request #171 from pysmo/codecov-token

tests: add codecov token to workflow
- Merge pull request #172 from pysmo/time-array

feat: add time_array function
- Merge pull request #173 from pysmo/remove-converters

feat: remove converters from mini classes
- Updates and some code cleanup
- Merge pull request #174 from pysmo/updates

chore: updates and some code cleanup
- Merge pull request #175 from pysmo/gh-pages

ci: add gh-pages workflow
- Tweaks to docs and add python 3.13 to matrix ([#176](https://github.com/pysmo/pysmo/issues/176))
- Merge pull request #177 from pysmo/unix_time

feat: add unix_time_array function
- **(deps-dev)** Bump notebook from 7.0.7 to 7.2.2
- Merge pull request #178 from pysmo/dependabot/pip/notebook-7.2.2

chore(deps-dev): bump notebook from 7.0.7 to 7.2.2
- **(deps)** Bump codecov/codecov-action from 4 to 5
- Merge pull request #179 from pysmo/dependabot/github_actions/codecov/codecov-action-5

chore(deps): bump codecov/codecov-action from 4 to 5
- **(deps-dev)** Bump tornado from 6.4.1 to 6.4.2
- Merge pull request #180 from pysmo/dependabot/pip/tornado-6.4.2

chore(deps-dev): bump tornado from 6.4.1 to 6.4.2
- Merge pull request #181 from pysmo/jupyter-lab

docs: switch to jupyter lab, update packages
- Merge pull request #182 from pysmo/signal-correlate

feat: add delay function
- Cut function
- Merge pull request #185 from pysmo/func-cut

Feat: cut function
- Remove methods and use functions only
- Merge pull request #186 from pysmo/no-methods

refactor: remove methods and use functions only
- Merge pull request #187 from pysmo/generic-funcs

feat: use generic types in functions
- Merge pull request #188 from pysmo/time2index

feat: add time2index function
- Use timedelta instaed of float for seimsmogram.delta
- Merge pull request #189 from pysmo/seis-delta-as-timedelta

refactor: use timedelta instaed of float for seimsmogram.delta
- Merge pull request #190 from pysmo/func-mode

feat: add clone arg to functions
- Split sacio module into rendered and non-rendered files
- Merge pull request #191 from pysmo/split-sacio

refactor: split sacio module into rendered and non-rendered files
- Merge pull request #192 from pysmo/mini-clones

feat: add clone and copy funcs
- Add CNAME file for gh-pages
- Merge pull request #193 from pysmo/update-tutorial

docs: update tutorial
- Merge pull request #194 from pysmo/sacio-iztype

feat: prevent changing header value if it is also zero time
- Merge pull request #196 from pysmo/windowed-normalise

feat: allow restricting max value search to window when normalising s…
- Switch to uv ([#199](https://github.com/pysmo/pysmo/issues/199))
- Merge pull request #200 from pysmo/iccs-pick

feat: iccs pick function
- Merge pull request #201 from pysmo/padded-iccs-plots

feat: add padding to iccs plots
- Merge pull request #202 from pysmo/iccs-tw-pick

feat: add iccs time window picker
- Merge pull request #203 from pysmo/iccs-equal-seis-len

fix: ensure iccs seismogram lengths are always equal
- Merge pull request #204 from pysmo/docs-relative-paths

docs: use relative paths for images and other pages
- Merge pull request #205 from pysmo/iccs-return-figs-optional

feat: make showing iccs figures optional
- Merge pull request #206 from pysmo/iccs-concurrent

feat: add concurrent processing to iccs
- Merge pull request #207 from pysmo/noise-example

docs: update noise example
- Merge pull request #208 from pysmo/docs-how-to-use

docs: add a small paragraph on how to use the documentation
- Use httpx instead of requests
- Merge pull request #209 from pysmo/httpx

refactor: use httpx instead of requests
- Use pathlib a bit more
- Merge pull request #210 from pysmo/use-pathlib

refactor: use pathlib a bit more
- Potential fix for code scanning alert no. 5: Workflow does not contain permissions

Co-authored-by: Copilot Autofix powered by AI <62310815+github-advanced-security[bot]@users.noreply.github.com>
- Merge pull request #211 from pysmo/alert-autofix-5

Potential fix for code scanning alert no. 5: Workflow does not contain permissions
- Potential fix for code scanning alert no. 3: Workflow does not contain permissions

Co-authored-by: Copilot Autofix powered by AI <62310815+github-advanced-security[bot]@users.noreply.github.com>
- Merge pull request #212 from pysmo/alert-autofix-3

Potential fix for code scanning alert no. 3: Workflow does not contain permissions
- Update time2index and related functions
- Merge pull request #213 from pysmo/update-seis-funcs

refactor: update time2index and related functions
- Merge pull request #214 from pysmo/iccs-resample

feat: resample seismograms in iccs
- Merge pull request #215 from pysmo/func-pad

feat: add pad function
- Merge pull request #216 from pysmo/iccs-limits

feat: add checks for iccs timewindow and pick updates
- Merge pull request #217 from pysmo/uuid-shortener

feat: add uuid_shortener function
- Merge pull request #218 from pysmo/pick-min-ccnorm

feat: iccs-select-ccnorm function
- Merge pull request #219 from pysmo/fix-sorted

fix: add key to sorted call
- Merge pull request #220 from pysmo/add-titles-to-figures

feat: add titles to iccs figures
- Merge pull request #221 from pysmo/progressive-scroll

feat: add progressive scrolling to min_ccnorm selecter and add option…
- Merge pull request #222 from pysmo/fix-ccnorm-with-all

fix: index was out of bounds with --all
- Merge pull request #223 from pysmo/iccs-allow-selecting-index0

fix: allow selecing index 0
- Clean up code and make sure to use np functions where applicable
- Merge pull request #224 from pysmo/use-np-functions

refactor: clean up code and make sure to use np functions where appli…
- Merge pull request #225 from pysmo/station-loc-channel

feat: add channel and location to station type
- Merge pull request #226 from pysmo/func-window

feat: add windows function and add py3.14
- Merge pull request #227 from pysmo/iccs-window

feat(iccs): taper on outside of window
- Move to ./src directory
- Merge pull request #228 from pysmo/src-dir

chore: move to ./src directory
- Merge pull request #229 from pysmo/zensical

docs: switch to zensical
- Merge pull request #230 from pysmo/new-tutorial

docs: simpler tutorial
- Merge pull request #231 from pysmo/docs-split-usage

docs: split usage into smaller sections
- Merge pull request #232 from pysmo/docs-update-dev

docs: update development section
- Merge pull request #233 from pysmo/docs-faqs

docs: add FAQs
- Merge pull request #234 from pysmo/fix-sacstation-setter

fix: correct type in sacstation.elevation setter
- **(tools-iccs)** Clarify types of prepared seismograms used in iccs
- Merge pull request #235 from pysmo/refactor-iccs-context

refactor(tools-iccs): Clarify types of prepared seismograms used in iccs
- Merge pull request #236 from pysmo/new-readme

docs: add more details to readme
- **(sacio)** Add retries to IRIS web service requests and tests
- Merge pull request #237 from pysmo/sacio-retries

Add retries to test_iris_service
- Merge pull request #239 from pysmo/hatch-vcs

ci: use dynamic versioning

### 🚀 New Features

- Add methods corresponding to functions to mini class
- Add Event type and MiniEvent class
- Sacio.py can read SAC version 7 files
- RuntimeError when trying to read invalid SAC file.
- Use nix dev environment ([#153](https://github.com/pysmo/pysmo/issues/153))
- Add time_array function
- Remove converters from mini classes
- Add unix_time_array function
- Add delay function
- Use generic types in functions
- Add time2index function
- Add clone arg to functions
- Add clone and copy funcs
- Prevent changing header value if it is also zero time
- Allow restricting max value search to window when normalising seismogram
- Add initial ICCS implementation ([#198](https://github.com/pysmo/pysmo/issues/198))
- Iccs pick function
- Add padding to iccs plots
- Add iccs time window picker
- Make showing iccs figures optional
- Add concurrent processing to iccs
- Resample seismograms in iccs
- Add pad function
- Add checks for iccs timewindow and pick updates
- Add uuid_shortener function
- Iccs-select-ccnorm function
- Add titles to iccs figures
- Add progressive scrolling to min_ccnorm selecter and add option to include all seismograms
- Add channel and location to station type
- Add windows function and add py3.14
- **(iccs)** Taper on outside of window

## [1.0.0-dev0] - 2023-08-18

### 🐛 Bug Fixes

- Fix typo

### 🔍 Other Changes

- Add code linting to Makefile and clean up code a bit
- Add github actions workflow for testing
- Add codecov to github action
- Change codecov report filetype to xml
- Remove travis stuff and update badge in readme
- Remove extra bracket in README
- Add coverage filename to gitignore
- Merge pull request #44 from pysmo/github-actions

GitHub actions
- Add version badge to readme
- Add pypi badges
- Add build action
- Really add build action...
- Merge pull request #45 from pysmo/build

Build
- Add path to artifact download so that the pypi action finds build
- Bump version to 0.8.0-dev1 to test package upload to pypi-test
- Add quickstart to README
- Update readme to show how to install from github directly
- Next version will be stable 1.0.0
- New sacheaders ([#46](https://github.com/pysmo/pysmo/issues/46))

* Move from storing header values inside the discriptor to the instance

* Update short description of the module
- Add protocols and rewrite functions to use them
- Merge pull request #47 from pysmo/seisproto

Add protocols and rewrite functions to use them
- Introduction ([#49](https://github.com/pysmo/pysmo/issues/49))

* Update deps and a bit of documentation.
- Update installation instructions.
- Merge pull request #51 from pysmo/doc-getting-started

Update installation instructions.
- Add devcontainer config
- Merge pull request #52 from pysmo/devcontainer

Add devcontainer config
- Documentation - Fundamentals ([#53](https://github.com/pysmo/pysmo/issues/53))

* Documentation - Fundamentals

* Remove whitespace to fix linting, add ignoring type back
- Seismogram Protocol ([#55](https://github.com/pysmo/pysmo/issues/55))

* Move protocols into their own directory

* Replace 'pass' with ellipses

* syncing (squash me)

* sync

* Fix tying errors

* Update packages

* jday (day of year) starts at 1, not 0

* Add linting to "make test"

* Fix some type hinting issues

* Calculate end time properly

* Add more type checks to sac headers

* Seismogram protocol

Some changes to the SAC class to take into account some differences betwenn sac headers and python classes (e.g. time resolution).
Unit tests for SAC as a Seismogram.

* Update action versions

* Also update action versions in test config
- Fix documentation ([#57](https://github.com/pysmo/pysmo/issues/57))

* Change python version for rtd

* Specify os to run docs build on

* Use python 3.10 to build docs

* add typing-extensions to requirements.txt in docs folder
- Furo ([#58](https://github.com/pysmo/pysmo/issues/58))

* Switch docs theme to furo, set newer package versions in pyproject.toml and fix some stuff to work with new versions

* add furo to docs requirements

* add workflow to build docs for pull requests
- Merge pull request #59 from pysmo/pysmo_V1

Move Pysmo v1 dev into master branch
- Use newer pypi-publish action
- Add some tests for the Station protocol

Also add checks for sane latitude and longitude values when changing them in sacio
- Skip publishing to test pypi on untagged commits
- Merge pull request #60 from pysmo/sac_station

Sac station
- Add tests for event protocol
- Merge pull request #61 from pysmo/sac_event

Add tests for event protocol
- First draft of intro section
- Merge pull request #66 from pysmo/first-steps

First draft of intro section
- Bump requests from 2.30.0 to 2.31.0

Bumps [requests](https://github.com/psf/requests) from 2.30.0 to 2.31.0.
- [Release notes](https://github.com/psf/requests/releases)
- [Changelog](https://github.com/psf/requests/blob/main/HISTORY.md)
- [Commits](https://github.com/psf/requests/compare/v2.30.0...v2.31.0)

---
updated-dependencies:
- dependency-name: requests
  dependency-type: direct:production
...

Signed-off-by: dependabot[bot] <support@github.com>
- Merge pull request #62 from pysmo/dependabot/pip/requests-2.31.0

Bump requests from 2.30.0 to 2.31.0
- Event is too generic as a type -> Epicenter and Hypcenter ([#67](https://github.com/pysmo/pysmo/issues/67))

* Replace Event protocol class with Epicenter and Hypocenter

* Add 2nd example in tutorial
- Update readme to fit in better with the documentation. ([#68](https://github.com/pysmo/pysmo/issues/68))
- New Documentation Structure ([#70](https://github.com/pysmo/pysmo/issues/70))

* New Documentation Structure
* Move everything to myst (markdown)
- Edit Makefile to run also on windows
- Merge pull request #72 from pysmo/win-makefile

Edit Makefile to run also on windows
- Remove "core" directory and reorganise psymo content
- Merge pull request #73 from pysmo/rearrange

Remove "core" directory and reorganise psymo content
- Add readme files to source directory
- Merge pull request #74 from pysmo/readmes

Add readme files to source directory
- Use nested classes in SAC class ([#77](https://github.com/pysmo/pysmo/issues/77))

* Use nested classes in SAC class

Instead of adding attributes directly to the SAC class, add nested classes for e.g. Seismogram, Station, etc.

* Update tutorial to use nested classes

* Update docstrings in functions for nested classes

* Remove unused type ignore.
- Add Mini classes ([#78](https://github.com/pysmo/pysmo/issues/78))
- Normalize function and test file for the func ([#76](https://github.com/pysmo/pysmo/issues/76))

* Normalize function and test file for the func

* Make normalize compatible with nested classes.

- Update docstring in normalize function
- Fix types in test_normalize.py

---------

Co-authored-by: Simon Lloyd <smlloyd@gmail.com>
- Cleanup tests

- define fixtures for all tests in conftest.py
- replicate source directory structure
- Merge pull request #79 from pysmo/cleanup-tests

Cleanup tests
- Documentation for "types"
- Merge pull request #80 from pysmo/doc-types

Documentation for "types"
- Update dependencies
- Merge pull request #83 from pysmo/updates

Update dependencies
- Bug fix in normalize function
- Merge pull request #81 from pysmo/bugfix-func-normalize

Bug fix in normalize function
- Classes documentation
- Merge pull request #84 from pysmo/doc-classes

Classes documentation
- Add docs for functions
- Merge pull request #85 from pysmo/doc-funcs

Add docs for functions
- Add tools documentation
- Merge pull request #86 from pysmo/docs-tools

Add tools documentation
- Add inherited attributes to SAC documentation
- Merge pull request #87 from pysmo/doc-sac-inheritance

add inherited attributes to SAC documentation
- Added instructions for setting up dev env on Windows ([#82](https://github.com/pysmo/pysmo/issues/82))

* Added instructions for setting up dev env on Windows

* Changes to dev env section of the docs

- Moved Setting up Windows section under Requirements
- Created separate subsection under Requirements for Pandocs

* small changes to windows setup

---------

Co-authored-by: Simon Lloyd <smlloyd@gmail.com>
- Update packages

* Update packages
* Small fix in sacio (type -> isinstance)
- Merge pull request #92 from pysmo/updates

Update packages
- Update Devcontainer Config ([#93](https://github.com/pysmo/pysmo/issues/93))

* Seems complicated to get it working on both docker and podman, so focus on just docker for now.
* Add gitattributes to fix line ending issues on windows.
* Install poetry via devcontainer features
- Don't run make notebook on attach
- Test with tox and add windows to matrix ([#94](https://github.com/pysmo/pysmo/issues/94))
- Fix spaces in tox.ini
- Ignore additinal coverage files
- Add lib/defaults.py

Defaults used throughout pysmo should be kept in one place.
- Merge pull request #95 from pysmo/libdefaults

Add lib/defaults.py
- Change tox config
- Merge pull request #96 from pysmo/tox

Change tox config
- Update packages
- Merge pull request #97 from pysmo/updates

Update packages
- Create tox venv without docs packages
- Merge pull request #98 from pysmo/tox

Create tox venv without docs packages
- Update noise tool to use pysmo types
- Merge pull request #101 from pysmo/noise

Update noise tool to use pysmo types
- Bump tornado from 6.3.2 to 6.3.3

Bumps [tornado](https://github.com/tornadoweb/tornado) from 6.3.2 to 6.3.3.
- [Changelog](https://github.com/tornadoweb/tornado/blob/master/docs/releases.rst)
- [Commits](https://github.com/tornadoweb/tornado/compare/v6.3.2...v6.3.3)

---
updated-dependencies:
- dependency-name: tornado
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] <support@github.com>
- Merge pull request #100 from pysmo/dependabot/pip/tornado-6.3.3

Bump tornado from 6.3.2 to 6.3.3
- Added content to contributing section of docs ([#88](https://github.com/pysmo/pysmo/issues/88))

* Filled the development workflow section in contrib

* Added documentation for contributing section of the docs

* Add "what are contributions?" section.

* Fixed line width and link references

* Remove some common git stuff and add some content particular to pysmo.

---------

Co-authored-by: Simon Lloyd <smlloyd@gmail.com>
Co-authored-by: Simon Lloyd <smlloyd@users.noreply.github.com>
- Add rules of the land chapter to docs. ([#102](https://github.com/pysmo/pysmo/issues/102))

* Add rules of the land chapter to docs.

* Add explicit package versions to docs/requirements.txt

* Add docs-export to Makefile.
- Update "more on types" section
- Merge pull request #103 from pysmo/docs-more-on-types

Update "more on types" section

## [0.8.0] - 2021-08-23

### 🔍 Other Changes

- Added two methods to sacio.SacIO: read_data and from_data. It will allow to read a SAC file from memory, for example, if the file comes from a URL request, avoid to save it into a temporary file.
Added a test to check the read_data works.
- It was a mistake when reading the data section of the SAC file. Solved.
- Added SacIO.from_iris
Renamed from_data to from_buffer
Removed duplicated code at SacIO (SacIO.from_file calls SacIO.from_buffer)
- Removed a debug print
- Merge pull request #43 from heltena/adding-SacIO.from_data

Added two methods to sacio.SacIO: read_data and from_data
- Add contributors to README
- Minor code cleanup
- Add update command to Makefile
- Update dependencies
- Update docs to show use of poetry instead of pipenv
- Next version will be 0.8.0

## [0.7.7] - 2021-06-29

### 🔍 Other Changes

- Fix formatting and add publish option in Makefile
- Add codecov hook to travis.yml
- Add codecov badge to readme
- Merge pull request #34 from pysmo/codecov

Codecov
- Fix typo
- Fix enum header bug and update dependancies
- Merge pull request #41 from pysmo/fix-iztype-error

Fix enum header bug and update dependancies
- Be sure to convert enumerated headers to int
- Merge pull request #42 from pysmo/fix-iztype-error

be sure to convert enumerated headers to int
- Bump version to 0.7.7

## [0.7.6] - 2020-12-14

### 🔍 Other Changes

- Switch from pipenv to poetry
- Move poetry install to install step
- Remove init from makefile
- Merge pull request #32 from pysmo/poetry

Use Poetry instead of Pipenv
- Setup.py not needed with poetry
- Add readthedocs CI files
- Specify additional docs to build
- Can we pip install local package
- Merge pull request #33 from pysmo/readthedocs

Readthedocs

## [0.7.5] - 2019-08-19

### 🔍 Other Changes

- Use yaml.safe_load instead of yaml.load.

This change mitigates the issue in CVE-2017-18342.
- Merge pull request #28 from pysmo/yaml-safe-load

Use yaml.safe_load instead of yaml.load.
- Update Makefile
- Ensure all python versions in travis.yml are used
- Update installation instructions for conda users.
- Merge pull request #29 from pysmo/conda-install

Update installation instructions for conda users.
- Check if pipenv is already installed before running pip install pipenv
- Change heading for conda installation
- Add development docs.
- Merge pull request #30 from pysmo/dev-docs

Add development docs.
- Update packages

## [0.7.4] - 2019-01-11

### 🔍 Other Changes

- Make __init__.py more concise.
- Add derived headers kztime and kzdate. ([#25](https://github.com/pysmo/pysmo/issues/25))

* Add derived headers kztime and kzdate.

- kztime and kztime are printed in ISO format
- additional code cleanups

* Python2 compatibility fixes since datetime is different in py2/py3
- Add some conda installation instructions.
- Add .python-version to .gitignore
- Pipenv ([#26](https://github.com/pysmo/pysmo/issues/26))

* Switch to pipenv

* python 3.7 fix for travis.

* Also build html docs within pipenv
- Remove py2 ([#27](https://github.com/pysmo/pysmo/issues/27))

Require python>=3.6

## [0.7.3] - 2018-12-05

### 🔍 Other Changes

- Use pytest for SacIO tests. ([#23](https://github.com/pysmo/pysmo/issues/23))

* Use pytest for SacIO tests.
- SacIO objects now can be pickled and deep copied.

- Also instead of raising an error undefined SAC header fields return None
- Merge pull request #24 from pysmo/deepcopy

SacIO objects now can be pickled and deep copied.

## [0.7.2] - 2018-12-04

### 🔍 Other Changes

- Sacio2 ([#15](https://github.com/pysmo/pysmo/issues/15))

* Rename SacFile class to SacIO.

- Change directory structure
- Changes to a SacIO object are now _not_ directly written to a file

Signed-off-by: Simon M. Lloyd <simon@slloyd.net>

* Add some documentation for from_file method

* Change path for sac in setup.py

* Change python3 version back to 3.6 - Travis doesn't do 3.7 yet.
- Make setup.py read requirements.txt
- Merge pull request #16 from pysmo/setupreqs

Make setup.py read requirements.txt
- Check validity of headers.

Header values to the python object have to be compatible with the SAC format to prevent errors writing to a file.
- Use try/except instead of if for <header_value>.rstrip()
- Merge pull request #17 from pysmo/safeheader

Check validity of headers.
- Recommend using virtualenv for installation.
- Add virtualenv to installation instructions.
- Add virtualenv to installation instructions.
- Merge branch 'master' of github.com:pysmo/pysmo
- Ensure SacIO is used instead of SacFile in the documentation.
- Fix typo in docs.
- Fix typo in docs.
- Rename SacFile -> SacIO in sacfunc.py
- Use include_package_data instead of data_files.
- Merge pull request #19 from pysmo/issue18

Use include_package_data instead of data_files.
- Use short paths for core modules in example docstrings.
- Fix typo and adjust requirements.txt to install scpiy 1.1
- Merge pull request #20 from pysmo/paths

Import all core modules
- Fix bug where sacheader descriptor was shared across instances.
- Merge pull request #21 from pysmo/sacinit

Fix bug where sacheader descriptor is shared across instances.
- Cleanup using pylint ([#22](https://github.com/pysmo/pysmo/issues/22))

* Cleanup using pylint
* Mark sacheader constants as internal.

## [0.6.1] - 2018-09-28

### 🔍 Other Changes

- Initial sphinx documentation
- Documentation structure done, still need content though.
- Add more documentation. Add scm_version to setuptools.
- Move use('Agg') further up.
- Merge pull request #14 from pysmo/sphinx

Sphinx
- Add pip installation instructions.

## [0.6.0] - 2018-09-10

### 🔍 Other Changes

- Don't track .DS_Store files.
- Convert to py3

decode bytes (b’…’) outside.
- Setup travis
- Merge pull request #4 from pysmo/travis

setup travis
- Remove itertools for python3 compatibility
- Remove itertools for python3 compatibility
- Merge branch 'issue2' of github.com:pysmo/sac into issue2
- Merge pull request #3 from pysmo/issue2

Remove itertools for python3 compatibility
- Adjust setup.py for pkgutil and move pysmo source to root directory.
- Merge pull request #5 from pysmo/pkgutil

Adjust setup.py for pkgutil and move pysmo source to root directory.
- Basic read/write tests for sacio
- Merge pull request #6 from pysmo/unittests

Basic read/write tests for sacio
- Fix bytencoding for py3
- Merge pull request #7 from pysmo/struct-error

Fix bytencoding for py3
- Store SAC header meta information in a separate yaml file.
- Add pyyaml to requirements
- Add yml file to setup.py - not installed otherwise
- Merge pull request #8 from pysmo/yaml

Store SAC header field information in a separate yml file
- Clean up code in sacfunc.py and add tests for each function defined there. ([#9](https://github.com/pysmo/pysmo/issues/9))
- Add gitter notification to travis
- Import future for forwards compatiblility

* Add future imports for compatibility.

* Add future to requirements.
- Place SAC header fields in a separate descriptor class.

Also adjusted logic in sacfile class to match this.
- Merge pull request #11 from pysmo/sep-header

Place SAC header fields in a separate descriptor class.
- Rename sacfile to SacFile.

This is for PEP8 naming. With sacfile = SacFile
backwards compatibility is maintained.
- Merge pull request #12 from pysmo/rename

Rename sacfile to SacFile.
- Move 'tools' into this repo, version bump to 0.6
- Merge pull request #13 from pysmo/include-tools

Move 'tools' into this repo, version bump to 0.6
- Update README.md

## [0.5.1] - 2014-08-07

### 🐛 Bug Fixes

- Fixed merge

### 🔍 Other Changes

- Initial commit
- Initial import of pysmo.sac
- Minor formatting changes
- Need init.py in pysmo dir so that sac part is picked up
- Small cleanup
added small sac2xy function
- Ade
- Update README.md
- Update README.md
- Temp save for sac
- Reverted
- Filename wrong
- Merge pull request #1 from pysmo/fix-sac

Fix sac
- New version
- Don't want to track the buld directory
- Change

