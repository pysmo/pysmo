"""Constrained type aliases used for runtime validation in pysmo.

These are [`Annotated`][typing.Annotated] type aliases with
[`beartype`][] validators that enforce value constraints (e.g.
positivity, range). They are not the same as pysmo types (protocol
classes); instead, they are used as type annotations within pysmo
to ensure attribute values meet expected constraints.
"""

from typing import Annotated
from pandas import Timedelta
from beartype.vale import Is

# Reusable Validators
_is_unit = Is[lambda x: 0.0 <= x <= 1.0]
_is_positive = Is[lambda x: x > 0]
_is_negative = Is[lambda x: x < 0]
_is_non_negative = Is[lambda x: x >= 0]
_is_positive_timedelta = Is[lambda x: x.total_seconds() > 0]
_is_negative_timedelta = Is[lambda x: x.total_seconds() < 0]
_is_non_negative_timedelta = Is[lambda x: x.total_seconds() >= 0]

UnitFloat = Annotated[float, _is_unit]
"""Float between 0.0 and 1.0."""

PositiveNumber = Annotated[float | int, _is_positive]
"""Positive Numbers (Float or Int)."""

NegativeNumber = Annotated[float | int, _is_negative]
"""Negative Numbers (Float or Int)."""

NonNegativeNumber = Annotated[float | int, _is_non_negative]
"""Non-negative Numbers (Float or Int)."""

PositiveTimedelta = Annotated[Timedelta, _is_positive_timedelta]
"""Positive Timedelta."""

NegativeTimedelta = Annotated[Timedelta, _is_negative_timedelta]
"""Negative Timedelta."""

NonNegativeTimedelta = Annotated[Timedelta, _is_non_negative_timedelta]
"""Non-negative Timedelta (includes 0 total_seconds)."""
