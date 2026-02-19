"""
Validators for pysmo classes using [`attrs`][attrs].
"""

from pandas import Timestamp
from datetime import timezone
from attrs import Attribute
from typing import Any


def datetime_is_utc(_: Any, attribute: Attribute, value: Timestamp | None) -> None:
    """Ensure [`pandas.Timestamp`][pandas.Timestamp] objects have `#!py tzdata=timezone.utc` set."""
    if value is None:
        return
    if value.tzinfo != timezone.utc:
        raise TypeError(
            f"Timestamp object {attribute} doesn't have tzdata=timezone.utc"
        )
