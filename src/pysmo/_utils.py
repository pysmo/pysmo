from collections.abc import Sequence
from typing import Any, cast

from attrs import AttrsInstance, fields


def as_sequence[T](value: T | Sequence[T]) -> Sequence[T]:
    """Normalise a single item or a sequence of items to a sequence, always.

    A bare `str`/`bytes` value is treated as one item, not iterated
    character-by-character, even though both satisfy `Sequence` themselves.
    """
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return value
    # cast: the Sequence[T] case returned above, but mypy can't narrow an unbounded T out of `value`.
    return cast(Sequence[T], [value])


def export_module_names(globals_dict: dict[str, Any], module_name: str) -> None:
    """Set `__module__` on every object in `__all__` to the calling module's name.

    Args:
        globals_dict: The globals() dictionary of the calling module.
        module_name: The name of the calling module (usually __name__).
    """
    all_names = globals_dict.get("__all__", [])

    for name in all_names:
        obj = globals_dict.get(name)
        if obj is None or not hasattr(obj, "__module__"):
            continue
        try:
            obj.__module__ = module_name
        except AttributeError:
            # `TypeAliasType` (a `type X = ...` alias) has a read-only
            # `__module__`; griffe resolves it via `__all__` re-export anyway.
            pass


# Defining either __getstate__ or __setstate__ makes attrs' `auto_detect` stop
# generating both, so a slotted class that only needs to reset a few fields on
# pickle has to reimplement the whole dance. These two helpers are that shared
# reimplementation.


def attrs_getstate(
    instance: AttrsInstance, overrides: dict[str, Any]
) -> dict[str, Any]:
    """Build pickle state for a slotted attrs instance, with `overrides` applied.

    Returns a field-name-to-value dict covering every field on `instance`,
    each `overrides` entry substituted. Pair with
    [`attrs_setstate`][pysmo._utils.attrs_setstate] in a class's
    `__getstate__` / `__setstate__`.

    Args:
        instance: The attrs instance being pickled.
        overrides: Field name to replacement value, for fields (a live
            connection, an in-memory cache, a lock) whose pickled state must
            be reset rather than carried over.
    """
    state = {f.name: getattr(instance, f.name) for f in fields(type(instance))}
    state.update(overrides)
    return state


def attrs_setstate(instance: AttrsInstance, state: dict[str, Any]) -> None:
    """Restore attrs instance state from `attrs_getstate` via `object.__setattr__`.

    Bypasses converters, validators and `on_setattr` hooks: restoring a
    prior state is not a mutation they should run on, and a hook may assume
    fields restored after it are already set.
    """
    for name, value in state.items():
        object.__setattr__(instance, name, value)
