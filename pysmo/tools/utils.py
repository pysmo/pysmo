"""Pysmo's little helpers."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID


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


def uuid_shortener(uuids: Sequence[UUID], min_length: int = 4) -> dict[str, UUID]:
    """Shorten a sequence of UUIDs to their shortest unique representation.

    Parameters:
        uuids: UUIDs to shorten.
        min_length: Minimum length of the shortened UUID strings.

    Returns:
        Dictionary mapping shortened UUID strings to their original UUID objects.

    Raises:
        ValueError: If an empty sequence is provided as input.
        ValueError: If `min_length` is not between 1 and 36.

    Examples:
        ```python
        >>> import uuid
        >>> from pysmo.tools.utils import uuid_shortener
        >>>
        >>> uuids = [uuid.uuid4() for _ in range(100)]
        >>> for k, v in sorted(uuid_shortener(uuids).items()):
        ...     print(f"{k} -> {v}")
        ...
        01d7 -> 01d74256-3860-4ab6-96a4-02f23ae8cc93
        03c7 -> 03c72ba8-d605-4770-8a63-f881ffd0f9d5
        080a -> 080aadfb-e7c9-4b26-9141-25c63a9bedd4
        0e51 -> 0e51f30d-c6a7-4e39-84b0-32ccd7c524a5
        ...
        >>>
        ```
    """
    if len(uuids) == 0:
        raise ValueError("Cannot shorten empty sequence of UUIDs.")

    if not (1 <= min_length <= 36):
        raise ValueError("min_length must be between 1 and 36.")

    str_uuids = list(map(str, uuids))

    for length in range(min_length, 37):  # UUIDs are 36 characters long
        shortened = [u[:length] for u in str_uuids]
        if len(set(shortened)) == len(uuids):
            return {u[:length]: uuid for u, uuid in zip(str_uuids, uuids)}

    # Fallback to full UUIDs if necessary (like that's going to happen...)
    return {str(u): u for u in uuids}
