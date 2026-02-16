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
        def check_normalized(seis: Seismogram) -> None:
            assert np.max(np.abs(seis.data)) <= 1.0

        modified = assert_seismogram_modification(
            seismogram,
            normalize,
            custom_assertions=check_normalized
        )

With snapshot testing (recommended for comprehensive data validation):

    from pysmo.functions import gauss

    def test_gauss(seismogram: Seismogram, snapshot) -> None:
        # Snapshot captures entire data array, not just single indices
        modified = assert_seismogram_modification(
            seismogram,
            gauss,
            Tn=50,
            alpha=50,
            snapshot=snapshot
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
- Optionally captures complete data snapshots for comprehensive validation
"""

from pysmo import Seismogram
from copy import deepcopy
from typing import Callable, Any
import numpy as np


def assert_seismogram_modification(
    seismogram: Seismogram,
    modification_func: Callable[..., Seismogram | None],
    *args: Any,
    custom_assertions: Callable[[Seismogram], None] | None = None,
    snapshot: Any = None,
    **kwargs: Any,
) -> Seismogram:
    """Test that a seismogram modification function works correctly with both clone modes.

    This helper function tests modification functions that support both:
    1. clone=True: Returns a new modified Seismogram
    2. clone=False (default): Modifies the Seismogram in-place

    It verifies that both approaches produce identical results and runs any
    custom assertions on the modified seismogram. Optionally uses syrupy snapshots
    to capture and verify the complete modified data array.

    Args:
        seismogram: The input Seismogram to be modified (any implementation).
        modification_func: The function that modifies the seismogram.
            Must accept the seismogram as first argument and support a 'clone'
            parameter.
        *args: Positional arguments to pass to modification_func (after seismogram).
        custom_assertions: Optional callback function that receives the modified
            seismogram and performs custom validation. Should raise AssertionError
            if validation fails.
        snapshot: Optional syrupy snapshot fixture for capturing the modified
            seismogram data. When provided, the entire data array will be compared
            against the snapshot, ensuring comprehensive validation beyond single
            index checks.
        **kwargs: Keyword arguments to pass to modification_func (except 'clone').

    Returns:
        The cloned modified seismogram (result of calling with clone=True).

    Raises:
        AssertionError: If clone and in-place modifications produce different results,
            if custom_assertions fail, or if snapshot comparison fails.

    Example:
        >>> from pysmo.functions import normalize
        >>> def check_normalized(seis: Seismogram) -> None:
        ...     assert np.max(np.abs(seis.data)) <= 1.0
        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     custom_assertions=check_normalized
        ... )

        With snapshot testing:
        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     snapshot=snapshot  # pytest fixture
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
    assert len(cloned_modified) == len(
        inplace_modified
    ), "Clone and in-place modifications have different lengths"

    # Run custom assertions if provided
    if custom_assertions is not None:
        custom_assertions(cloned_modified)

    # Snapshot testing if provided
    if snapshot is not None:
        # Create a serializable representation of the seismogram data
        snapshot_data = {
            "data": cloned_modified.data.tolist(),
            "begin_time": cloned_modified.begin_time.isoformat(),
            "delta": cloned_modified.delta.total_seconds(),
            "length": len(cloned_modified),
        }
        assert snapshot_data == snapshot

    return cloned_modified
