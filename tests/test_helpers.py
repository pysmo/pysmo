"""Helper functions for testing Seismogram modifications.

This module provides reusable test utilities for verifying functions that modify
Seismogram objects. The helpers are designed to work with any Seismogram Protocol
implementation (SacSeismogram, MiniSeismogram, or future classes).

Usage Examples
--------------

Basic usage with custom assertions:

    from pysmo.functions import normalize
    import numpy as np

    def test_normalize(seismogram: Seismogram) -> None:
        def check_normalised(seis: Seismogram) -> None:
            assert np.max(np.abs(seis.data)) <= 1.0

        modified = assert_seismogram_modification(
            seismogram,
            normalize,
            custom_assertions=check_normalised
        )

With expected data validation (recommended for numerical accuracy):

    from pysmo.functions import gauss

    def test_gauss(seismogram: Seismogram) -> None:
        # Load or compute expected output
        expected_output = np.load('expected_gauss_output.npy')

        # Validate with tolerance for floating-point precision
        modified = assert_seismogram_modification(
            seismogram,
            gauss,
            Tn=50,
            alpha=50,
            expected_data=expected_output,
            rtol=1e-7  # relative tolerance
        )

With syrupy snapshot testing (recommended for regression testing):

    from pysmo.functions import gauss

    def test_gauss_snapshot(seismogram: Seismogram, snapshot) -> None:
        # Use syrupy snapshot to track expected output
        # Data is automatically rounded to 6 decimals for snapshot storage
        modified = assert_seismogram_modification(
            seismogram,
            gauss,
            Tn=50,
            alpha=50,
            expected_data=snapshot
        )

With additional arguments:

    from pysmo.functions import crop

    def test_crop(seismogram: Seismogram) -> None:
        new_begin = seismogram.begin_time + timedelta(seconds=10)
        new_end = seismogram.end_time - timedelta(seconds=10)

        def check_times(seis: Seismogram) -> None:
            assert seis.begin_time >= new_begin
            assert seis.end_time <= new_end

        assert_seismogram_modification(
            seismogram,
            crop,
            new_begin,
            new_end,
            custom_assertions=check_times
        )

With keyword arguments:

    from pysmo.functions import pad

    def test_pad(seismogram: Seismogram) -> None:
        assert_seismogram_modification(
            seismogram,
            pad,
            seismogram.begin_time,
            seismogram.end_time,
            custom_assertions=lambda s: len(s) == len(seismogram)
        )

The helper automatically:
- Tests both clone=True and clone=False modes
- Verifies both produce identical results
- Checks data arrays match using numpy.testing.assert_array_equal
- Validates time attributes (begin_time, delta, length)
- Runs your custom assertions on the modified seismogram
- Optionally validates against expected data with configurable tolerance
- Optionally validates against syrupy snapshots for regression testing
"""

from pysmo import Seismogram
from copy import deepcopy
from typing import Callable, Any
import numpy as np

try:
    from syrupy.assertion import SnapshotAssertion
except ImportError:
    SnapshotAssertion = None  # type: ignore


def assert_seismogram_modification(
    seismogram: Seismogram,
    modification_func: Callable[..., Seismogram | None],
    *args: Any,
    custom_assertions: Callable[[Seismogram], None] | None = None,
    expected_data: np.ndarray | Any | None = None,
    rtol: float = 1e-7,
    atol: float = 0.0,
    **kwargs: Any,
) -> Seismogram:
    """Test that a seismogram modification function works correctly with both clone modes.

    This helper function tests modification functions that support both:
    1. clone=True: Returns a new modified Seismogram
    2. clone=False (default): Modifies the Seismogram in-place

    It verifies that both approaches produce identical results and runs any
    custom assertions on the modified seismogram. Optionally compares against
    expected data using numpy array assertions with configurable tolerances or
    syrupy snapshot testing.

    Args:
        seismogram: The input Seismogram to be modified (any implementation).
        modification_func: The function that modifies the seismogram.
            Must accept the seismogram as first argument and support a 'clone'
            parameter.
        *args: Positional arguments to pass to modification_func (after seismogram).
        custom_assertions: Optional callback function that receives the modified
            seismogram and performs custom validation. Should raise AssertionError
            if validation fails.
        expected_data: Optional expected data to compare against. Accepts:
            - np.ndarray: Uses np.testing.assert_allclose() with tolerance
            - SnapshotAssertion (syrupy snapshot): Rounds data to 6 decimals with
              np.around() before comparison to reduce snapshot size
            - None: No data validation (default)
        rtol: Relative tolerance for expected_data comparison (default: 1e-7).
            Only used when expected_data is an np.ndarray.
        atol: Absolute tolerance for expected_data comparison (default: 0.0).
            Only used when expected_data is an np.ndarray.
        **kwargs: Keyword arguments to pass to modification_func (except 'clone').

    Returns:
        The cloned modified seismogram (result of calling with clone=True).

    Raises:
        AssertionError: If clone and in-place modifications produce different results,
            if custom_assertions fail, or if expected_data comparison fails.

    Examples:
        Basic usage with custom assertions:

        >>> from pysmo.functions import normalize
        >>> def check_normalised(seis: Seismogram) -> None:
        ...     assert np.max(np.abs(seis.data)) <= 1.0
        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     custom_assertions=check_normalised
        ... )

        With expected data validation:

        >>> expected = np.array([...])  # expected output
        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     expected_data=expected,
        ...     rtol=1e-5  # relative tolerance
        ... )

        With syrupy snapshot:

        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     expected_data=snapshot  # syrupy snapshot fixture
        ... )
    """
    # Test with clone=True - should return a new modified seismogram
    cloned_modified = modification_func(seismogram, *args, clone=True, **kwargs)
    assert (
        cloned_modified is not None
    ), "Function with clone=True should return a Seismogram"

    # Test with clone=False (in-place) - should modify and return None or the seismogram
    inplace_copy = deepcopy(seismogram)
    result = modification_func(inplace_copy, *args, clone=False, **kwargs)

    # Handle functions that may return the seismogram or None
    inplace_modified = result if result is not None else inplace_copy

    # Verify both approaches produce identical data
    np.testing.assert_array_equal(
        cloned_modified.data,
        inplace_modified.data,
        err_msg="Clone and in-place modifications produced different data",
    )

    # Verify time attributes match
    assert (
        cloned_modified.begin_time == inplace_modified.begin_time
    ), "Clone and in-place modifications have different begin_time"
    assert (
        cloned_modified.delta == inplace_modified.delta
    ), "Clone and in-place modifications have different delta"
    assert len(cloned_modified.data) == len(
        inplace_modified.data
    ), "Clone and in-place modifications have different lengths"

    # Run custom assertions if provided
    if custom_assertions is not None:
        custom_assertions(cloned_modified)

    # Validate against expected data if provided
    if expected_data is not None:
        # Check if expected_data is a syrupy snapshot
        if SnapshotAssertion is not None and isinstance(
            expected_data, SnapshotAssertion
        ):
            # Use syrupy's assert_match method for snapshot comparison
            # Round data to 6 decimals to reduce snapshot size and improve precision control
            rounded_data = np.around(cloned_modified.data, decimals=6)
            expected_data.assert_match(rounded_data)
        elif isinstance(expected_data, np.ndarray):
            # Use numpy's assert_allclose for array comparison
            np.testing.assert_allclose(
                cloned_modified.data,
                expected_data,
                rtol=rtol,
                atol=atol,
                err_msg="Modified data does not match expected data within tolerance",
            )
        else:
            # Fallback: try direct comparison (might be a list or other sequence)
            np.testing.assert_allclose(
                cloned_modified.data,
                expected_data,
                rtol=rtol,
                atol=atol,
                err_msg="Modified data does not match expected data within tolerance",
            )

    return cloned_modified
