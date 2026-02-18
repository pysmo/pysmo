"""Constrained type aliases used for runtime validation in pysmo.

These are [`Annotated`][typing.Annotated] type aliases with
[`beartype`][] validators that enforce value constraints (e.g.
positivity, range). They are not the same as pysmo types (protocol
classes); instead, they are used as type annotations within pysmo
to ensure attribute values meet expected constraints.
"""

from typing import Annotated
import numpy as np
from beartype.vale import Is


def _td64_to_seconds(td: np.timedelta64) -> float:
    """Convert timedelta64 to seconds as float."""
    return td.astype("timedelta64[us]").astype(np.int64) / 1_000_000.0


# Reusable Validators
_is_unit = Is[lambda x: 0.0 <= x <= 1.0]
_is_positive = Is[lambda x: x > 0]
_is_negative = Is[lambda x: x < 0]
_is_non_negative = Is[lambda x: x >= 0]
_is_positive_timedelta64 = Is[lambda x: _td64_to_seconds(x) > 0]
_is_negative_timedelta64 = Is[lambda x: _td64_to_seconds(x) < 0]
_is_non_negative_timedelta64 = Is[lambda x: _td64_to_seconds(x) >= 0]

UnitFloat = Annotated[float, _is_unit]
"""Float between 0.0 and 1.0."""

PositiveNumber = Annotated[float | int, _is_positive]
"""Positive Numbers (Float or Int)."""

NegativeNumber = Annotated[float | int, _is_negative]
"""Negative Numbers (Float or Int)."""

NonNegativeNumber = Annotated[float | int, _is_non_negative]
"""Non-negative Numbers (Float or Int)."""

PositiveTimedelta64 = Annotated[np.timedelta64, _is_positive_timedelta64]
"""Positive timedelta64."""

NegativeTimedelta64 = Annotated[np.timedelta64, _is_negative_timedelta64]
"""Negative timedelta64."""

NonNegativeTimedelta64 = Annotated[np.timedelta64, _is_non_negative_timedelta64]
"""Non-negative timedelta64 (includes 0 total_seconds)."""

# Legacy aliases for backwards compatibility (deprecated)
PositiveTimedelta = PositiveTimedelta64
NegativeTimedelta = NegativeTimedelta64
NonNegativeTimedelta = NonNegativeTimedelta64
