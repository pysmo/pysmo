"""Constrained type aliases used in pysmo."""

from datetime import timezone
from typing import Annotated

import pandas as pd
from annotated_types import Ge, Gt, Interval, Lt, Timezone

# ---------------------------------------------------------------------------
# Numeric Type Aliases with Constraints
# ---------------------------------------------------------------------------

type UnitFloat = Annotated[float | int, Interval(ge=0, le=1)]
"""Float between 0.0 and 1.0, or int that is 0 or 1."""

type PositiveNumber = Annotated[int | float, Gt(0)]
"""Positive Numbers (Float or Int) greater than 0."""

type NegativeNumber = Annotated[int | float, Lt(0)]
"""Negative Numbers (Float or Int) less than 0."""

type NonNegativeNumber = Annotated[int | float, Ge(0)]
"""Non-negative Numbers (Float or Int) greater than or equal to 0."""

# ---------------------------------------------------------------------------
# pandas Timedelta/Timestamp Type Aliases with Constraints
# ---------------------------------------------------------------------------

_ZERO_TD = pd.Timedelta(0)

type PositiveTimedelta = Annotated[pd.Timedelta, Gt(_ZERO_TD)]
"""Positive Timedelta."""

type NegativeTimedelta = Annotated[pd.Timedelta, Lt(_ZERO_TD)]
"""Negative Timedelta."""

type NonNegativeTimedelta = Annotated[pd.Timedelta, Ge(_ZERO_TD)]
"""Non-negative Timedelta (includes 0 total_seconds)."""

type UtcTimestamp = Annotated[pd.Timestamp, Timezone(tz=timezone.utc)]
"""Timestamp with utc timezone information."""
