"""Helper functions for testing Seismogram modifications.

This module provides reusable test utilities for verifying functions that modify
Seismogram objects. The helpers are designed to work with any Seismogram Protocol
implementation (SacSeismogram, MiniSeismogram, or future classes).
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
    **kwargs: Any,
) -> Seismogram:
    """Test that a seismogram modification function works correctly with both clone modes.

    This helper function tests modification functions that support both:
    1. clone=True: Returns a new modified Seismogram
    2. clone=False (default): Modifies the Seismogram in-place

    It verifies that both approaches produce identical results and runs any
    custom assertions on the modified seismogram.

    Args:
        seismogram: The input Seismogram to be modified (any implementation).
        modification_func: The function that modifies the seismogram.
            Must accept the seismogram as first argument and support a 'clone'
            parameter.
        *args: Positional arguments to pass to modification_func (after seismogram).
        custom_assertions: Optional callback function that receives the modified
            seismogram and performs custom validation. Should raise AssertionError
            if validation fails.
        **kwargs: Keyword arguments to pass to modification_func (except 'clone').

    Returns:
        The cloned modified seismogram (result of calling with clone=True).

    Raises:
        AssertionError: If clone and in-place modifications produce different results,
            or if custom_assertions fail.

    Example:
        >>> from pysmo.functions import normalize
        >>> def check_normalized(seis: Seismogram) -> None:
        ...     assert np.max(np.abs(seis.data)) <= 1.0
        >>> modified = assert_seismogram_modification(
        ...     my_seismogram,
        ...     normalize,
        ...     custom_assertions=check_normalized
        ... )
    """
    # Test with clone=True - should return a new modified seismogram
    cloned_modified = modification_func(seismogram, *args, clone=True, **kwargs)
    assert cloned_modified is not None, "Function with clone=True should return a Seismogram"

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
    assert (
        len(cloned_modified) == len(inplace_modified)
    ), "Clone and in-place modifications have different lengths"

    # Run custom assertions if provided
    if custom_assertions is not None:
        custom_assertions(cloned_modified)

    return cloned_modified
