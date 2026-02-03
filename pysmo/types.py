"""Custom types for pysmo."""

from typing import Annotated
from datetime import timedelta
from beartype.vale import Is

# Reusable Validators
_is_positive = Is[lambda x: x > 0]
_is_non_negative = Is[lambda x: x >= 0]
_is_unit = Is[lambda x: 0.0 <= x <= 1.0]
_is_positive_timedelta = Is[lambda x: x.total_seconds() > 0]
_is_non_negative_timedelta = Is[lambda x: x.total_seconds() >= 0]

UnitFloat = Annotated[float, _is_unit]
"""Float between 0.0 and 1.0."""

PositiveNumber = Annotated[float | int, _is_positive]
"""Positive Numbers (Float or Int)."""

NonNegativeNumber = Annotated[float | int, _is_non_negative]
"""Non-negative Numbers (Float or Int)."""

PositiveTimedelta = Annotated[timedelta, _is_positive_timedelta]
"""Positive Timedelta."""

NonNegativeTimedelta = Annotated[timedelta, _is_non_negative_timedelta]
"""Non-negative Timedelta (includes 0 total_seconds)."""
