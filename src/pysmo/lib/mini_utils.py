"""Mini utils."""

import inspect
import types
from typing import TypeAliasType, cast, get_args, get_protocol_members

from pysmo import _BaseMini, _BaseProto
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


def _structural_match(obj: object, proto: type) -> bool:
    """Whether `obj` (an instance or a class) has every member `proto` requires.

    Name-based structural check — signatures and types are a type-checker
    concern, not checked here. Uses `inspect.getattr_static`, so a member
    defined as a property whose getter would raise still counts as present.
    """
    for member in get_protocol_members(proto):
        try:
            inspect.getattr_static(obj, member)
        except AttributeError:
            return False
    return True


def proto2mini(proto: type[_AnyProto]) -> tuple[type[_AnyMini], ...]:
    """Returns valid Mini classes that implement the given pysmo Protocol.

    This function resolves the input protocol (handling modern type aliases and
    unions) and filters the available 'Mini' classes to find those that
    structurally implement it.

    Args:
        proto: A pysmo type (e.g., `Location`, `Event`) or a type alias
            pointing to one.

    Returns:
        A tuple of concrete Mini classes (e.g., `MiniLocation`, `MiniEvent`)
        that satisfy the interface defined by `proto`.

    Examples:
        Get all Mini classes that implement the `Location` protocol:

        ```python
        >>> from pysmo.lib.mini_utils import proto2mini
        >>> from pysmo import Location, Event
        >>> proto2mini(Location)
        (<class 'pysmo.MiniStation'>, <class 'pysmo.MiniEvent'>, <class 'pysmo.MiniLocation'>, <class 'pysmo.MiniLocationWithDepth'>)
        >>>
        ```

        Works with Type Aliases and Unions (if the input is a union, it returns
        Minis matching *any* of the protocols in that union):

        ```python
        >>> type MyProto = Location | Event
        >>> proto2mini(MyProto)
        (<class 'pysmo.MiniStation'>, <class 'pysmo.MiniEvent'>, <class 'pysmo.MiniLocation'>, <class 'pysmo.MiniLocationWithDepth'>)
        >>>
        ```
    """

    target_protos = _get_flattened_types(proto)
    possible_minis = _get_flattened_types(_AnyMini)

    seen: set[type[_AnyMini]] = set()
    result: list[type[_AnyMini]] = []
    for mini in possible_minis:
        mini_types = matching_pysmo_types(mini)
        if any(tp in mini_types for tp in target_protos) and mini not in seen:
            seen.add(mini)
            result.append(mini)
    return tuple(result)


def matching_pysmo_types(obj: object) -> tuple[type[_AnyProto], ...]:
    """Returns pysmo types that objects may be an instance of.

    Args:
        obj: The object (or class) to check.

    Returns:
        Pysmo types that `obj` is an instance of.

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
        if _structural_match(obj, proto):
            matches.append(cast(type[_AnyProto], proto))

    return tuple(matches)
