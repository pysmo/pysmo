"""Annotated type aliases that document value constraints.

Each alias pairs a base type with an
[`annotated_types`](https://github.com/annotated-types/annotated-types)
constraint. They are used for attribute and parameter annotations where a
value has to satisfy more than its type, and the constraint is shown in the
[API reference][pysmo].
"""

from datetime import UTC
from typing import Annotated

import pandas as pd
from annotated_types import Ge, Gt, Interval, Le, Lt, Predicate, Timezone

# ---------------------------------------------------------------------------
# Numeric Type Aliases with Constraints
# ---------------------------------------------------------------------------

type UnitFloat = Annotated[float | int, Interval(ge=0, le=1)]
"""Number between 0 and 1, inclusive."""

type PositiveInt = Annotated[int, Gt(0)]
"""Integer greater than 0."""

type PositiveNumber = Annotated[int | float, Gt(0)]
"""Number greater than 0."""

type NonZeroNumber = Annotated[int | float, Predicate(lambda x: x != 0)]
"""Number other than 0, of either sign."""

type NegativeNumber = Annotated[int | float, Lt(0)]
"""Number less than 0."""

type NonNegativeNumber = Annotated[int | float, Ge(0)]
"""Number greater than or equal to 0."""

# ---------------------------------------------------------------------------
# pandas Timedelta/Timestamp Type Aliases with Constraints
# ---------------------------------------------------------------------------

_ZERO_TD = pd.Timedelta(0)

type PositiveTimedelta = Annotated[pd.Timedelta, Gt(_ZERO_TD)]
"""Timedelta greater than 0."""

type NegativeTimedelta = Annotated[pd.Timedelta, Lt(_ZERO_TD)]
"""Timedelta less than 0."""

type NonNegativeTimedelta = Annotated[pd.Timedelta, Ge(_ZERO_TD)]
"""Timedelta greater than or equal to 0."""

type NonPositiveTimedelta = Annotated[pd.Timedelta, Le(_ZERO_TD)]
"""Timedelta less than or equal to 0."""

type UtcTimestamp = Annotated[pd.Timestamp, Timezone(tz=UTC)]
"""Timestamp with a UTC timezone."""
