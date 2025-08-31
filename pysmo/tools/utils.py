"""Pysmo's little helpers."""

from collections.abc import Sequence
from datetime import datetime, timedelta


def average_datetimes(datetimes: Sequence[datetime]) -> datetime:
    """Average a sequence of datetimes.

    Parameters:
        datetimes: Datetimes to average.

    Returns:
        Datetime representing average of all datetimes.

    Raises:
        ValueError: If an empty sequence is provides as input.
    """
    if len(datetimes) == 0:
        raise ValueError("Cannot average empty sequence of datetimes.")
    reference_time = datetimes[0]
    seconds = sum((i - reference_time).total_seconds() for i in datetimes[1:])
    return reference_time + timedelta(seconds=seconds / len(datetimes))
