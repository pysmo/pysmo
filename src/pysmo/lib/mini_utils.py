"""Mini utils."""

from pysmo import _BaseMini, _BaseProto
from pysmo.tools import _ToolsMini, _ToolsProto
from typing import TypeAliasType, get_args, cast
import types

__all__ = ["proto2mini", "matching_pysmo_types"]

type _AnyProto = _BaseProto | _ToolsProto
"Type alias for any pysmo Protocol class."

type _AnyMini = _BaseMini | _ToolsMini
"Type alias for any pysmo Mini class."


def _get_flattened_types(tp: object) -> tuple[type, ...]:
    """Recursively unwraps aliases and flattens '|' unions.

    Assumes NO usage of typing.Union or typing.Optional!
    """
    # 1. Unwrap aliases
    while isinstance(tp, TypeAliasType):
        tp = tp.__value__

    # 2. Check ONLY for modern '|' unions
    if isinstance(tp, types.UnionType):
        flattened_args: list[type] = []
        for member in get_args(tp):
            flattened_args.extend(_get_flattened_types(member))
        return tuple(flattened_args)

    # 3. Base Case: Single class
    return (cast(type, tp),)


def _safe_check(obj: object, proto: type) -> bool:
    """Safely checks isinstance/issubclass for Protocols with data members."""
    try:
        if isinstance(obj, type):
            return issubclass(obj, proto)
        return isinstance(obj, proto)
    except TypeError:
        # Fallback: Structural check using annotations
        proto_anns = getattr(proto, "__annotations__", {})
        target = obj if isinstance(obj, type) else type(obj)
        target_anns = getattr(target, "__annotations__", {})
        return all(key in target_anns for key in proto_anns)


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

    target_proto = _get_flattened_types(proto)[0]
    possible_minis = _get_flattened_types(_AnyMini)

    return tuple(
        mini for mini in possible_minis if target_proto in matching_pysmo_types(mini)
    )


def matching_pysmo_types(obj: object) -> tuple[type[_AnyProto], ...]:
    """Returns pysmo types that objects may be an instance of.

    Args:
        obj: Name of the object to check.

    Returns:
        Pysmo types for which `obj` is an instance of.

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
        if _safe_check(obj, proto):
            matches.append(cast(type[_AnyProto], proto))

    return tuple(matches)
