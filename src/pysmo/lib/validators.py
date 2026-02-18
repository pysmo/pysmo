"""
Validators for pysmo classes using [`attrs`][attrs].
"""

import numpy as np
from attrs import Attribute
from typing import Any


def datetime64_is_utc(_: Any, attribute: Attribute, value: np.datetime64 | None) -> None:
    """Ensure datetime64 values are in UTC (which they always are by definition).
    
    NumPy datetime64 values don't have timezone information, but are assumed to be UTC.
    This validator is maintained for API compatibility but doesn't need to check anything
    since datetime64 is timezone-naive and treated as UTC by convention.
    """
    if value is None:
        return
    # datetime64 is always in UTC by convention in pysmo
    # No validation needed, but we keep the function for compatibility


# Legacy alias for backwards compatibility
datetime_is_utc = datetime64_is_utc
