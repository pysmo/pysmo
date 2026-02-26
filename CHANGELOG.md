# Changelog

All notable changes to the **pysmo** project will be documented in this file.

## [Unreleased]

### 🐛 Bug Fixes

- **(iccs)** Fix save cancel callback on buttons
- Distinguish between required/non-required sac time headers

### 📚 Documentation

- Remove unused mkdocs-macros-plugin

### 🔍 Other Changes

- Install pandas

### 🔧 Refactoring

- Migrate from stdlib datetime to pandas Timestamp/Timedelta ([#252](https://github.com/pysmo/pysmo/issues/252))
- **(tools-iccs)** Make figures modular for easier re-use
- Use 2 descriptors instead of 1 complicated one for sac timestamps
- **(signal)** Add filter registry decorator ([#257](https://github.com/pysmo/pysmo/issues/257))
- **(types)** [**breaking**] Remove __len__ method from Seismogram

### 🚀 New Features

- **(tools-signal)** Add multi-delay functions ([#249](https://github.com/pysmo/pysmo/issues/249))
- **(tools-signal)** Add mccc function

## [1.0.0.dev0](https://github.com/pysmo/pysmo/compare/v0.8.0...v1.0.0.dev0) - 2026-02-17

### ⚙️ DevOps & Infrastructure

- Combine coverage results before uploading and add osx
- Add dependabot for gh actions
- Add gh-pages workflow
- Use poetry with mkdocs
- Use dynamic versioning

### 🎨 Styling

- Switch to formatting with black

### 🐛 Bug Fixes

- Fix typo
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
- **(cliff)** Add more filters
- **(faqs)** Add diagram showing how pysmo relates to third party modules

### 📦 Miscellaneous

- Ignore black commit in git blame
- Update packages
- Add py312 to matrix
- Don't install pandoc, don't run post attach commands ([#143](https://github.com/pysmo/pysmo/issues/143))
- Update packages and run tox lint and report on py312
- Cleanup CI config
- Update packages and format some code
- Update pytest to version 8 ([#160](https://github.com/pysmo/pysmo/issues/160))
- Update dependencies
- Update deps
- Upload hidden files as artifacts for codecov ci step
- Updates and some code cleanup
- Tweaks to docs and add python 3.13 to matrix ([#176](https://github.com/pysmo/pysmo/issues/176))
- Add CNAME file for gh-pages
- Switch to uv ([#199](https://github.com/pysmo/pysmo/issues/199))
- Move to ./src directory

### 🔍 Other Changes

- Add code linting to Makefile and clean up code a bit
- Add github actions workflow for testing
- Add codecov to github action
- Change codecov report filetype to xml
- Remove travis stuff and update badge in readme
- Remove extra bracket in README
- Add coverage filename to gitignore
- Add version badge to readme
- Add pypi badges
- Add build action
- Really add build action...
- Add path to artifact download so that the pypi action finds build
- Bump version to 0.8.0-dev1 to test package upload to pypi-test
- Add quickstart to README
- Update readme to show how to install from github directly
- Next version will be stable 1.0.0
- New sacheaders ([#46](https://github.com/pysmo/pysmo/issues/46))
- Add protocols and rewrite functions to use them
- Introduction ([#49](https://github.com/pysmo/pysmo/issues/49))
- Update installation instructions.
- Add devcontainer config
- Documentation - Fundamentals ([#53](https://github.com/pysmo/pysmo/issues/53))
- Seismogram Protocol ([#55](https://github.com/pysmo/pysmo/issues/55))
- Fix documentation ([#57](https://github.com/pysmo/pysmo/issues/57))
- Furo ([#58](https://github.com/pysmo/pysmo/issues/58))
- Use newer pypi-publish action
- Add some tests for the Station protocol
- Skip publishing to test pypi on untagged commits
- Add tests for event protocol
- First draft of intro section
- Event is too generic as a type -> Epicenter and Hypcenter ([#67](https://github.com/pysmo/pysmo/issues/67))
- Update readme to fit in better with the documentation. ([#68](https://github.com/pysmo/pysmo/issues/68))
- New Documentation Structure ([#70](https://github.com/pysmo/pysmo/issues/70))
- Edit Makefile to run also on windows
- Remove "core" directory and reorganise psymo content
- Add readme files to source directory
- Use nested classes in SAC class ([#77](https://github.com/pysmo/pysmo/issues/77))
- Add Mini classes ([#78](https://github.com/pysmo/pysmo/issues/78))
- Normalize function and test file for the func ([#76](https://github.com/pysmo/pysmo/issues/76))
- Cleanup tests
- Documentation for "types"
- Update dependencies
- Bug fix in normalize function
- Classes documentation
- Add docs for functions
- Add tools documentation
- Add inherited attributes to SAC documentation
- Added instructions for setting up dev env on Windows ([#82](https://github.com/pysmo/pysmo/issues/82))
- Update packages
- Update Devcontainer Config ([#93](https://github.com/pysmo/pysmo/issues/93))
- Don't run make notebook on attach
- Test with tox and add windows to matrix ([#94](https://github.com/pysmo/pysmo/issues/94))
- Fix spaces in tox.ini
- Ignore additinal coverage files
- Add lib/defaults.py
- Change tox config
- Update packages
- Create tox venv without docs packages
- Update noise tool to use pysmo types
- Added content to contributing section of docs ([#88](https://github.com/pysmo/pysmo/issues/88))
- Add rules of the land chapter to docs. ([#102](https://github.com/pysmo/pysmo/issues/102))
- Update "more on types" section
- Bump version in pyproj.toml
- Modify build workflow to run on new tags
- Issue #65: providing error message from IRIS service ([#105](https://github.com/pysmo/pysmo/issues/105))
- Noise tests ([#106](https://github.com/pysmo/pysmo/issues/106))
- Add a bit more testing ([#107](https://github.com/pysmo/pysmo/issues/107))
- Rename _Sacio to SacIO and move it to pysmo/lib/io
- Use poetry to generate requirements.txt in readthedocs build
- Update deps
- Don't build singlehtml
- Add py.typed
- Small tweaks to test config
- Strip whitespaces and \x00 chars when reading sac files.
- Fix typo in mini module documentation
- Fix typo in makefile help string
- (feat) Add sac timestamps
- Cut function

### 🔧 Refactoring

- Move SAC helper classes inside SAC class
- Move functions into a single file
- Rewrite sacio as (pydantic) dataclass
- Use pydantic dataclass for mini classes
- Change clone_to_miniseismogram function to classmethod clone in MiniSeismogram
- Use attrs instead of pydantic
- Rename sacio jinja template file
- Rename sampling_rate to delta.
- Remove methods and use functions only
- Use timedelta instaed of float for seimsmogram.delta
- Split sacio module into rendered and non-rendered files
- Use httpx instead of requests
- Use pathlib a bit more
- Update time2index and related functions
- Clean up code and make sure to use np functions where applicable
- **(tools-iccs)** Clarify types of prepared seismograms used in iccs

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
- Retry from_iris on error status 500
- **(signal)** Add butterworth filters
- **(iccs)** Add bandpass filtering to iccs ([#248](https://github.com/pysmo/pysmo/issues/248))

### 🧪 Testing

- Rearrange test structure to match changes in src structure
- Re-organise test folders and fixtures.
- Lint with ruff instead of flake8
- Check tutorial notebook runs error free
- Add codecov token to workflow
- **(sacio)** Add retries to IRIS web service requests and tests
- Add common test helper script and use snapshots ([#243](https://github.com/pysmo/pysmo/issues/243))
- **(signal)** Add unit tests for butter filters
- Snapshot regression testing with 6-decimal rounding to seismogram functions ([#246](https://github.com/pysmo/pysmo/issues/246))
- **(signal)** Verify butterworth with sac implementation ([#247](https://github.com/pysmo/pysmo/issues/247))

## [0.8.0](https://github.com/pysmo/pysmo/compare/v0.7.7...v0.8.0) - 2021-08-23

### 🔍 Other Changes

- Added two methods to sacio.SacIO: read_data and from_data. It will allow to read a SAC file from memory, for example, if the file comes from a URL request, avoid to save it into a temporary file.
- It was a mistake when reading the data section of the SAC file. Solved.
- Added SacIO.from_iris
- Removed a debug print
- Add contributors to README
- Minor code cleanup
- Add update command to Makefile
- Update dependencies
- Update docs to show use of poetry instead of pipenv
- Next version will be 0.8.0

## [0.7.7](https://github.com/pysmo/pysmo/compare/v0.7.6...v0.7.7) - 2021-06-29

### 🔍 Other Changes

- Fix formatting and add publish option in Makefile
- Add codecov hook to travis.yml
- Add codecov badge to readme
- Fix typo
- Fix enum header bug and update dependancies
- Be sure to convert enumerated headers to int
- Bump version to 0.7.7

## [0.7.6](https://github.com/pysmo/pysmo/compare/v0.7.5...v0.7.6) - 2020-12-14

### 🔍 Other Changes

- Switch from pipenv to poetry
- Move poetry install to install step
- Remove init from makefile
- Setup.py not needed with poetry
- Add readthedocs CI files
- Specify additional docs to build
- Can we pip install local package

## [0.7.5](https://github.com/pysmo/pysmo/compare/v0.7.4...v0.7.5) - 2019-08-19

### 🔍 Other Changes

- Use yaml.safe_load instead of yaml.load.
- Update Makefile
- Ensure all python versions in travis.yml are used
- Update installation instructions for conda users.
- Check if pipenv is already installed before running pip install pipenv
- Change heading for conda installation
- Add development docs.
- Update packages

## [0.7.4](https://github.com/pysmo/pysmo/compare/v0.7.3...v0.7.4) - 2019-01-11

### 🔍 Other Changes

- Make __init__.py more concise.
- Add derived headers kztime and kzdate. ([#25](https://github.com/pysmo/pysmo/issues/25))
- Add some conda installation instructions.
- Add .python-version to .gitignore
- Pipenv ([#26](https://github.com/pysmo/pysmo/issues/26))
- Remove py2 ([#27](https://github.com/pysmo/pysmo/issues/27))

## [0.7.3](https://github.com/pysmo/pysmo/compare/v0.7.2...v0.7.3) - 2018-12-05

### 🔍 Other Changes

- Use pytest for SacIO tests. ([#23](https://github.com/pysmo/pysmo/issues/23))
- SacIO objects now can be pickled and deep copied.

## [0.7.2](https://github.com/pysmo/pysmo/compare/v0.6.1...v0.7.2) - 2018-12-04

### 🔍 Other Changes

- Sacio2 ([#15](https://github.com/pysmo/pysmo/issues/15))
- Make setup.py read requirements.txt
- Check validity of headers.
- Use try/except instead of if for <header_value>.rstrip()
- Recommend using virtualenv for installation.
- Add virtualenv to installation instructions.
- Add virtualenv to installation instructions.
- Ensure SacIO is used instead of SacFile in the documentation.
- Fix typo in docs.
- Fix typo in docs.
- Rename SacFile -> SacIO in sacfunc.py
- Use include_package_data instead of data_files.
- Use short paths for core modules in example docstrings.
- Fix typo and adjust requirements.txt to install scpiy 1.1
- Fix bug where sacheader descriptor was shared across instances.
- Cleanup using pylint ([#22](https://github.com/pysmo/pysmo/issues/22))

## [0.6.1](https://github.com/pysmo/pysmo/compare/v0.6.0...v0.6.1) - 2018-09-28

### 🔍 Other Changes

- Initial sphinx documentation
- Documentation structure done, still need content though.
- Add more documentation. Add scm_version to setuptools.
- Move use('Agg') further up.
- Add pip installation instructions.

## [0.6.0](https://github.com/pysmo/pysmo/compare/v0.5.1...v0.6.0) - 2018-09-10

### 🔍 Other Changes

- Don't track .DS_Store files.
- Convert to py3
- Setup travis
- Remove itertools for python3 compatibility
- Remove itertools for python3 compatibility
- Adjust setup.py for pkgutil and move pysmo source to root directory.
- Basic read/write tests for sacio
- Fix bytencoding for py3
- Store SAC header meta information in a separate yaml file.
- Add pyyaml to requirements
- Add yml file to setup.py - not installed otherwise
- Clean up code in sacfunc.py and add tests for each function defined there. ([#9](https://github.com/pysmo/pysmo/issues/9))
- Add gitter notification to travis
- Import future for forwards compatiblility
- Place SAC header fields in a separate descriptor class.
- Rename sacfile to SacFile.
- Move 'tools' into this repo, version bump to 0.6
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
- Ade
- Update README.md
- Update README.md
- Temp save for sac
- Reverted
- Filename wrong
- New version
- Don't want to track the buld directory
- Change

