"""
Validators for pysmo classes using [`attrs`][attrs].
"""

import pandas as pd
from attrs import Attribute
from typing import Any


def timestamp_is_utc(_: Any, attribute: Attribute, value: pd.Timestamp | None) -> None:
    """Ensure pandas Timestamp values are in UTC timezone.
    
    Args:
        _: Instance (unused).
        attribute: The attribute being validated.
        value: The Timestamp to validate.
        
    Raises:
        ValueError: If the Timestamp doesn't have UTC timezone.
    """
    if value is None:
        return
    if value.tz is None:
        raise ValueError(
            f"{attribute.name} must have UTC timezone. "
            f"Use pd.Timestamp(..., tz='UTC') or timestamp.tz_localize('UTC')."
        )
    if str(value.tz) != "UTC":
        raise ValueError(
            f"{attribute.name} must be in UTC timezone, got {value.tz}. "
            f"Use timestamp.tz_convert('UTC') to convert."
        )


# Legacy alias for backwards compatibility
datetime64_is_utc = timestamp_is_utc
datetime_is_utc = timestamp_is_utc
