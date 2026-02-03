"""
Validators for pysmo classes using [`attrs`][attrs].
"""

from datetime import datetime, timezone
from attrs import Attribute
from typing import Any


def datetime_is_utc(_: Any, attribute: Attribute, value: datetime | None) -> None:
    """Ensure [`datetime`][datetime.datetime] datetime objects have `#!py tzdata=timezone.utc` set."""
    if value is None:
        return
    if value.tzinfo != timezone.utc:
        raise TypeError(f"datetime object {attribute} doesn't have tzdata=timezone.utc")
