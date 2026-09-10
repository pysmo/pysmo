"""Validators for pysmo's `attrs` classes."""

from __future__ import annotations

import pandas as pd
from attrs import Attribute, validators

is_latitude = validators.and_(validators.ge(-90), validators.le(90))
"""`attrs` validator for a geographic latitude: -90 to 90 degrees, inclusive."""

# `gt(-180)`, not `ge`: `converters.to_longitude` folds -180 onto +180, so a real
# -180 is stored as +180 and never reaches this validator.
is_longitude = validators.and_(validators.gt(-180), validators.le(180))
"""`attrs` validator for a geographic longitude in degrees, paired with
`converters.to_longitude`."""

is_positive_timedelta = validators.and_(
    validators.instance_of(pd.Timedelta), validators.gt(pd.Timedelta(0))
)
"""`attrs` validator for a strictly positive `pandas.Timedelta`."""


def is_nonzero[T: int | float | complex | None](
    instance: object, attribute: Attribute[T], value: T
) -> None:
    """Ensure `value` is not exactly zero. Either sign is otherwise permitted."""
    if value == 0:
        raise ValueError(f"{attribute.name} must not be zero.")
