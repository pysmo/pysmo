# Migration from NumPy datetime64/timedelta64 to Pandas Timestamp/Timedelta

## Status: IN PROGRESS (Phase 1 Complete)

This document tracks the migration from NumPy datetime64/timedelta64 to pandas Timestamp/Timedelta as requested.

## Rationale

Pandas Timestamp and Timedelta provide several advantages:
- Native `.total_seconds()` method (works without helper functions)
- Built-in timezone support (Timestamp is timezone-aware)
- Better integration with pandas DataFrame/Series if needed in future
- More Pythonic API for time operations

## What Has Been Completed

### Phase 1: Core Type Definitions ✅

1. **Dependencies** (`pyproject.toml`)
   - Added `pandas>=2.2.0` to dependencies

2. **Type System** (`src/pysmo/typing.py`)
   - Changed `PositiveTimedelta`, `NegativeTimedelta`, `NonNegativeTimedelta` to use `pd.Timedelta`
   - Validators now use `.total_seconds()` directly (no helper needed)
   - Kept backwards compatibility aliases

3. **Defaults** (`src/pysmo/lib/defaults.py`)
   - `SEISMOGRAM_DEFAULTS.begin_time` now `pd.Timestamp(0, tz="UTC")`
   - `SEISMOGRAM_DEFAULTS.delta` now `pd.Timedelta(seconds=1)`

4. **Validators** (`src/pysmo/lib/validators.py`)
   - Changed `datetime64_is_utc` to `timestamp_is_utc`
   - Now validates that pandas Timestamp has UTC timezone
   - Kept backwards compatibility alias

5. **Protocol Classes**
   - `Seismogram` protocol (`src/pysmo/_types/_seismogram.py`):
     - `begin_time: pd.Timestamp` (with UTC timezone)
     - `delta: pd.Timedelta`
     - `end_time` property returns `pd.Timestamp`
   
   - `MiniSeismogram` class (`src/pysmo/_types/_seismogram.py`):
     - Updated to use `pd.Timestamp` and `pd.Timedelta`
     - Validator uses `timestamp_is_utc`
   
   - `Event` protocol (`src/pysmo/_types/_event.py`):
     - `time: pd.Timestamp` (with UTC timezone)
   
   - `MiniEvent` class (`src/pysmo/_types/_event.py`):
     - Updated to use `pd.Timestamp`

## What Needs to Be Done

### Phase 2: Implementation Classes

1. **SAC Class** (`src/pysmo/classes/_sac.py`)
   - Update `SacSeismogram` to use pandas types
   - Update `SacEvent` to use pandas types
   - Update `SacTimestamps` to use pandas types
   - Update SAC I/O to convert between SAC float times and pandas Timestamp

2. **ICCS Types** (`src/pysmo/tools/iccs/_types.py`)
   - Update `ICCSSeismogram` protocol
   - Update `MiniICCSSeismogram`
   - Update `_EphemeralSeismogram`

3. **ICCS Class** (`src/pysmo/tools/iccs/_iccs.py`)
   - Update `ICCS` class attributes to use pandas Timedelta
   - Update `ICCS_DEFAULTS`

### Phase 3: Functions

1. **Seismogram Functions** (`src/pysmo/functions/_seismogram.py`)
   - `crop()` - accept pd.Timestamp for begin/end
   - `pad()` - accept pd.Timestamp for begin/end
   - `resample()` - accept pd.Timedelta for delta
   - `taper()` - accept pd.Timedelta for ramp_width
   - `time2index()` - accept pd.Timestamp for time
   - `window()` - accept pd.Timestamp and pd.Timedelta
   - `normalize()` - accept pd.Timestamp for t1/t2

2. **Signal Processing** (`src/pysmo/tools/signal/`)
   - `_delay.py`: Decide on return type for delay arrays
     - Option A: Return numpy array with pd.Timedelta dtype
     - Option B: Return list of pd.Timedelta
     - Option C: Keep numpy timedelta64 for performance
   
3. **Noise Generation** (`src/pysmo/tools/noise.py`)
   - Update `generate_noise()` signature to accept pd.Timedelta
   - Already updated but may need adjustments

4. **ICCS Functions** (`src/pysmo/tools/iccs/_functions.py`)
   - Update all plotting and window calculations
   - Already partially updated but needs review

### Phase 4: Utils and Helpers

1. **Utils** (`src/pysmo/tools/utils.py`)
   - **Remove or simplify `to_seconds()`**: 
     - pandas Timedelta has native `.total_seconds()`
     - May still need for backwards compatibility
   
   - **Remove converter functions**: Probably not needed anymore
     - `datetimes_to_datetime64()` 
     - `datetime64_to_datetimes()`
     - `timedeltas_to_timedelta64()`
     - `timedelta64_to_timedeltas()`
   
   - **Update `average_datetimes()`**:
     - Should work with pd.Timestamp
     - May need adjustment for timezone handling

2. **SAC I/O** (`src/pysmo/lib/io/_sacio/`)
   - Update conversion between SAC float times and pandas Timestamp
   - Update `_lib.py` functions

### Phase 5: Tests

All test files need updates:

1. **Core Tests**
   - `tests/classes/test_sac.py` - Update to use pd.Timestamp/Timedelta
   - `tests/classes/mini/test_mini_seismogram.py` - Update examples
   - `tests/functions/test_seismogram.py` - Update all function tests

2. **Signal Tests**
   - `tests/tools/signal/test_delay.py` - Update delay calculations
   - `tests/tools/signal/filter/test_butter.py` - Update sampling rate calcs
   - `tests/tools/signal/filter/test_gauss.py` - Similar updates

3. **ICCS Tests**
   - `tests/tools/iccs/test_iccs.py` - Update window/context tests

4. **Utils Tests**
   - `tests/tools/test_tools_utils.py` - Update or remove converter tests

### Phase 6: Documentation

1. **Conventions** (`docs/usage/conventions.md`)
   - Update to explain pandas Timestamp/Timedelta usage
   - Explain timezone requirements (always UTC)
   - Provide examples

2. **Copilot Instructions** (`.github/copilot-instructions.md`)
   - Update to mention pandas types
   - Add best practices for working with pandas timestamps

3. **Docstrings**
   - Update all docstring examples to use pandas types
   - Ensure sybil tests pass

## Key Design Decisions

### Timezone Handling

- **All Timestamps MUST be UTC**: This is enforced by the `timestamp_is_utc` validator
- Use `pd.Timestamp(..., tz='UTC')` when creating timestamps
- Use `.tz_localize('UTC')` to add UTC timezone to naive timestamps
- Use `.tz_convert('UTC')` to convert from other timezones to UTC

### Array Returns

For functions that return arrays of time values (like `multi_delay()`):
- **Recommended**: Return numpy array with pandas Timedelta dtype
- This provides performance of numpy arrays with semantics of pandas
- Example: `np.array([pd.Timedelta(seconds=1), pd.Timedelta(seconds=2)])`

### Backwards Compatibility

- Keep alias functions where possible
- `datetime64_is_utc` kept as alias to `timestamp_is_utc`
- Old validator names maintained for compatibility

## Testing Strategy

1. **Unit Tests**: Update all assertions to work with pandas types
2. **Integration Tests**: Ensure SAC I/O roundtrip works correctly
3. **Docstring Tests**: Update all docstring examples (sybil will check them)
4. **Type Checking**: Ensure mypy passes with new types

## Potential Issues

1. **Performance**: pandas Timestamp may be slightly slower than numpy datetime64
   - Mitigate by using numpy arrays where performance critical
   - Profile before and after if concerned

2. **Dependency Weight**: pandas is a large dependency
   - Consider if the benefits outweigh the dependency cost
   - pandas is well-maintained and widely used in scientific Python

3. **SAC I/O**: Converting between SAC float times and pandas Timestamp
   - Need to ensure microsecond precision is maintained
   - Test edge cases (very old/new dates, leap seconds, etc.)

4. **Matplotlib Integration**: Need to ensure pandas Timestamp works with matplotlib
   - Should work seamlessly but test plotting functions

## Rollback Plan

If this migration proves problematic:
1. Revert to commit before this migration started
2. Consider staying with numpy datetime64/timedelta64
3. Or consider using Python's native datetime/timedelta with timezone support

## Next Steps

1. Complete Phase 2: Update SAC and ICCS implementation classes
2. Run basic tests to catch obvious errors early
3. Continue through phases 3-6 systematically
4. Run full test suite
5. Update documentation
6. Test with real-world seismology workflows
