"""Exceptions that are part of the pysmo protocol contract.

Implementations of the pysmo protocols raise these, so code written against a
protocol can catch them without knowing which class it was given.
"""

__all__ = ["MissingValueError"]


class MissingValueError(TypeError, ValueError):
    """Raised when an attribute is read whose value is not set.

    A concrete class may hold an attribute as optional when its protocol
    requires it. A SAC file without the `stla` header is one example. Reading
    such an attribute raises this error.

    It subclasses both `TypeError` and `ValueError`, so existing
    `except TypeError` and `except ValueError` clauses also catch it.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.exceptions import MissingValueError
        >>>
        >>> sac = SAC()
        >>> try:
        ...     sac.station.latitude
        ... except MissingValueError:
        ...     print("no station latitude")
        ...
        no station latitude
        >>>
        ```
    """
