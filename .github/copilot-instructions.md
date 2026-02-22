# GitHub Copilot Instructions for Pysmo

## Commands

```bash
make sync          # Install all dependencies (run first)
make tests         # Run full test suite (includes mypy)
make mypy          # Type checks only
make lint          # black --check + ruff check
make format        # Apply black formatting
```

Run a single test file or specific test:

```bash
uv run pytest tests/functions/test_seismogram.py
uv run pytest tests/functions/test_seismogram.py::test_crop
uv run pytest -k "test_crop"
```

## Architecture

Pysmo separates **types** (protocols), **storage** (concrete classes), and **processing** (functions/tools):

### Protocol layer (`src/pysmo/_types/`)

`Seismogram`, `Station`, `Event`, `Location`, `LocationWithDepth` are Python `Protocol` classes — they define interfaces via structural subtyping. Any class implementing the right attributes is compatible, no inheritance required.

### Mini classes (also in `src/pysmo/_types/`)

`MiniSeismogram`, `MiniStation`, etc. are minimal `attrs`-based reference implementations of each protocol. They use `@beartype` for runtime validation and are the default way to create pysmo objects programmatically.

### Concrete classes (`src/pysmo/classes/`)

`SAC` is the main concrete class, wrapping a SAC file via `SacIO`. It exposes nested objects (`sac.seismogram`, `sac.station`, `sac.event`) that implement the protocols by mapping SAC header values. New storage formats should follow this nesting pattern.

### Functions (`src/pysmo/functions/`)

Low-level building blocks operating on protocol types. Functions that modify seismograms follow a **clone pattern**: called without `clone` they mutate in place and return `None`; called with `clone=True` they return a `deepcopy`. Avoid `obj = fn(obj, clone=True)` — use in-place mutation instead.

### Tools (`src/pysmo/tools/`)

Higher-level processing modules (signal filtering, noise analysis, ICCS cross-correlation, etc.) built on top of `pysmo.functions`.

### Time types

All time values use **pandas** types:

- `pandas.Timestamp` for absolute times — must always be UTC (validated by `datetime_is_utc`)
- `pandas.Timedelta` for intervals (e.g. `delta`, durations)

### Constrained types (`src/pysmo/typing.py`)

`pysmo.typing` provides `Annotated` type aliases with `beartype` validators: `PositiveTimedelta`, `PositiveNumber`, `UnitFloat`, etc. Use these for attribute/parameter annotations where value constraints are needed.

## Code Style and Standards

### PEP 8 Compliance

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide for all Python code
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black default)
- Use blank lines to separate functions and classes
- Imports should be grouped: standard library, third-party, local
- Use ellipsis (`...`) for code that is not implemented yet, rather than `pass`
  or leaving it blank. Don't warn me that code using these is not doing anything.

### Code Formatting

- All code must pass **Black** formatting
  - Target Python versions: 3.12, 3.13, 3.14
  - Line length: 88 characters
  - Run `black .` before committing

- All code must pass **Ruff** linting
  - Configuration in `pyproject.toml`
  - Run `ruff check .` before committing
  - Fix issues with `ruff check --fix .`

### Language

- Use **British English** spelling in all:
  - Comments
  - Docstrings
  - Variable names
  - Documentation
  - Error messages
- Examples:
  - `colour` not `color`
  - `normalise` not `normalize`
  - `initialise` not `initialize`
  - `behaviour` not `behavior`
  - `centre` not `center`

### Documentation Style

#### Docstrings

- Use **Google Style** docstrings for all public functions, classes, and methods
- Format:

  ```python
  def function_name(param1: type1, param2: type2) -> return_type:
      """Brief one-line description.

      Longer description if needed, explaining the purpose and behaviour
      of the function in more detail.

      Args:
          param1: Description of param1.
          param2: Description of param2.
              Multi-line descriptions should be indented.

      Returns:
          Description of the return value.

      Raises:
          ErrorType: Description of when this error is raised.

      Examples:
          >>> function_name(value1, value2)
          expected_output
      """
  ```

#### Type Hints

- Use type hints for all function parameters and return values
- Use modern Python type syntax (Python 3.12+):
  - `list[str]` not `List[str]`
  - `dict[str, int]` not `Dict[str, int]`
  - `type1 | type2` not `Union[type1, type2]`
  - `type | None` not `Optional[type]`

### Testing

- Write tests for all new functionality
- Use pytest framework
- Tests should be in the `tests/` directory
- Use descriptive test names: `test_function_does_expected_behaviour`
- Try to mirror the directory structure of `src/pysmo/` in `tests/`
- **Sybil** runs all docstring examples in `src/` and `docs/` as tests — every `Examples:` block in a docstring is executed. Ensure examples are correct and executable. Use the `copy_testfiles` fixture (already wired in `conftest.py`) when examples reference `"example.sac"`.
- Snapshot tests use **syrupy** — call `snapshot.assert_match(value)`, with data rounded via `np.around(..., 6)` before comparison

### Commit Messages

- Use clear, descriptive commit messages
- Follow conventional commits format when appropriate
- Use British English spelling

## Review Priorities

- Take the above Code Style and Standards into account when reviewing pull requests
- Suggest improvements to code style, efficiency, documentation, and testing
- Suggest improvements to variable names, function names, and overall code readability
- Suggest newer syntax features where appropriate
- Check spelling
- Check if docstrings in existing code follow Google style and suggest improvements if needed

## Project-Specific Guidelines

### Seismology Domain

- Follow seismological conventions for variable names
- Use proper units and document them
- Maintain scientific accuracy in all calculations

### Dependencies

- Minimum Python version: 3.12, maximum 3.14
- Core dependencies: numpy, matplotlib, scipy, beartype, attrs, pandas
- Dependency management: `uv` with locked `uv.lock`; run `make sync` after pulling

### File Organisation

- Source code in `src/pysmo/`
- Tests in `tests/`
- Documentation in `docs/`
- Use appropriate module structure

## Before Committing

1. Run `make format` to apply black formatting
2. Run `make lint` to check formatting and linting
3. Run `make tests` to run the full test suite (includes mypy)
4. Check British English spelling
5. Ensure docstrings follow Google style
