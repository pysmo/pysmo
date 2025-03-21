from datetime import datetime, timezone
from attrs import Attribute
from typing import Any


def datetime_is_utc(_: Any, attribute: Attribute, value: datetime) -> None:
    if value.tzinfo != timezone.utc:
        raise TypeError(f"datetime object {attribute} doesn't have tzdata=timezone.utc")
