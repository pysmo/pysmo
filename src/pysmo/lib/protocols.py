"""Runtime helpers for pysmo's structural protocol types.

pysmo's protocols are not `runtime_checkable`, so conformance is normally a
type-checker concern. These helpers provide a deliberate, name-based
structural check for the few places that need one at runtime.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import get_protocol_members

from attrs import Attribute


def missing_protocol_members(obj: object, proto: type) -> list[str]:
    """Member names `proto` declares that `obj` (an instance or a class) lacks.

    Name-based: `inspect.getattr_static` is used, so a member defined as a
    property whose getter would raise still counts as present.
    """
    missing: list[str] = []
    for member in get_protocol_members(proto):
        try:
            inspect.getattr_static(obj, member)
        except AttributeError:
            missing.append(member)
    return missing


def has_protocol_members(obj: object, proto: type) -> bool:
    """Whether `obj` (an instance or a class) carries every member `proto` declares.

    The boolean inverse of `missing_protocol_members`: name-based, so a member
    defined as a property whose getter would raise still counts as present — a
    match guarantees the names exist, not that every access succeeds.
    """
    return not missing_protocol_members(obj, proto)


def satisfies_protocol[T](
    proto: type,
) -> Callable[[object, Attribute[T], T], None]:
    """Return an `attrs` validator requiring the value to structurally satisfy `proto`.

    The check is by member name (see `missing_protocol_members`). `T` is the
    decorated field's own type, inferred by attrs; the validator itself only
    reads the field name.
    """

    def _validate(instance: object, attribute: Attribute[T], value: T) -> None:
        missing = missing_protocol_members(value, proto)
        if missing:
            detail = f" (missing: {', '.join(sorted(missing))})"
            raise TypeError(
                f"{attribute.name} must satisfy the {proto.__name__} protocol{detail}."
            )

    return _validate
