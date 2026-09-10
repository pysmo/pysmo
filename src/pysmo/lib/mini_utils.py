"""Match objects and protocols to pysmo's Mini classes."""

import types
from typing import TypeAliasType, cast, get_args

from pysmo import _BaseMini, _BaseProto
from pysmo.lib.protocols import has_protocol_members
from pysmo.tools import _ToolsMini, _ToolsProto

__all__ = ["matching_pysmo_types", "proto2mini"]

type _AnyProto = _BaseProto | _ToolsProto
"Type alias for any pysmo Protocol class."

type _AnyMini = _BaseMini | _ToolsMini
"Type alias for any pysmo Mini class."


def _get_flattened_types(tp: object) -> tuple[type, ...]:
    """Recursively unwraps aliases and flattens '|' unions.

    Assumes NO usage of typing.Union or typing.Optional!
    """
    match tp:
        case TypeAliasType():
            # An alias may itself point at another alias, so keep unwrapping.
            return _get_flattened_types(tp.__value__)
        case types.UnionType():
            # Each member may be an alias or a nested union in its own right.
            return tuple(
                flat for member in get_args(tp) for flat in _get_flattened_types(member)
            )
        case _:
            return (cast(type, tp),)


def proto2mini(proto: type[_AnyProto]) -> tuple[type[_AnyMini], ...]:
    """Return the Mini classes that implement a given pysmo protocol.

    This function resolves the input protocol (handling modern type aliases and
    unions) and filters the available 'Mini' classes to find those that
    structurally implement it.

    Args:
        proto: A pysmo type (e.g., `Location`, `Event`) or a type alias
            pointing to one.

    Returns:
        A tuple of concrete Mini classes (e.g., `MiniLocation`, `MiniEvent`)
        that satisfy the interface defined by `proto`, ordered by class name.

    Examples:
        Get all Mini classes that implement the `Location` protocol:

        ```python
        >>> from pysmo.lib.mini_utils import proto2mini
        >>> from pysmo import Location, Event
        >>> proto2mini(Location)
        (<class 'pysmo.MiniEvent'>, <class 'pysmo.MiniLocation'>, <class 'pysmo.MiniLocationWithDepth'>, <class 'pysmo.MiniStation'>)
        >>>
        ```

        Works with Type Aliases and Unions (if the input is a union, it returns
        Minis matching *any* of the protocols in that union):

        ```python
        >>> type MyProto = Location | Event
        >>> proto2mini(MyProto)
        (<class 'pysmo.MiniEvent'>, <class 'pysmo.MiniLocation'>, <class 'pysmo.MiniLocationWithDepth'>, <class 'pysmo.MiniStation'>)
        >>>
        ```
    """

    target_protos = _get_flattened_types(proto)
    possible_minis = _get_flattened_types(_AnyMini)

    matches = {
        mini
        for mini in possible_minis
        if any(tp in matching_pysmo_types(mini) for tp in target_protos)
    }
    return tuple(sorted(matches, key=lambda tp: tp.__name__))


def matching_pysmo_types(obj: object) -> tuple[type[_AnyProto], ...]:
    """Return the pysmo types an object structurally satisfies.

    The check is name-based (see `has_protocol_members`): `obj` counts as
    matching a protocol when it carries every member name that protocol
    declares. Protocols have no runtime instance relationship, so this is not
    an `isinstance` test.

    Args:
        obj: The object (or class) to check.

    Returns:
        Pysmo types that `obj` structurally satisfies, ordered by type name.

    Examples:
        Pysmo types matching instances of
        [`MiniLocationWithDepth`][pysmo.MiniLocationWithDepth] or the class
        itself:

        ```python
        >>> from pysmo.lib.mini_utils import matching_pysmo_types
        >>> from pysmo import MiniLocationWithDepth
        >>>
        >>> mini = MiniLocationWithDepth(latitude=12, longitude=34, depth=56)
        >>> matching_pysmo_types(mini)
        (<class 'pysmo.Location'>, <class 'pysmo.LocationWithDepth'>)
        >>>
        >>> matching_pysmo_types(MiniLocationWithDepth)
        (<class 'pysmo.Location'>, <class 'pysmo.LocationWithDepth'>)
        >>>
        ```
    """

    matches: list[type[_AnyProto]] = []

    possible_protos = _get_flattened_types(_AnyProto)

    for proto in possible_protos:
        if has_protocol_members(obj, proto):
            matches.append(cast(type[_AnyProto], proto))

    return tuple(sorted(matches, key=lambda tp: tp.__name__))
