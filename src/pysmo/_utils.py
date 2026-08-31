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
    """Updates the __module__ attribute of all objects in __all__ to match the current module name.

    Args:
        globals_dict: The globals() dictionary of the calling module.
        module_name: The name of the calling module (usually __name__).
    """
    all_names = globals_dict.get("__all__", [])

    for name in all_names:
        obj = globals_dict.get(name)
        if obj is not None and hasattr(obj, "__module__"):
            obj.__module__ = module_name


def attrs_getstate(
    instance: AttrsInstance, overrides: dict[str, Any]
) -> dict[str, Any]:
    """Build pickle state for an attrs instance, replacing fields that must not survive a pickle round trip.

    For an attrs class with `slots=True` (the `@define` default), there is
    no `self.__dict__` to hand to the default pickling protocol, so state
    must be built from the class's own fields instead — the same thing
    attrs' own auto-generated `__getstate__` already does for any slotted
    class that defines no `__getstate__`/`__setstate__` of its own. This
    helper (paired with [`attrs_setstate`][pysmo._utils.attrs_setstate])
    exists only for the one thing attrs has no declarative hook for: forcing
    specific fields (a live connection, an in-memory cache, a lock) to a
    fresh value on every pickle, regardless of their current value. Once a
    class defines its own `__getstate__`/`__setstate__` — as any class using
    this helper must — attrs' `auto_detect` sees them and stops generating
    its own version entirely (it is all-or-nothing, the same mechanism that
    skips auto-generating `__repr__`/`__eq__` when a class defines its own),
    so there is no way to keep attrs' generated behaviour and only override
    a couple of fields; this helper reimplements that shared boilerplate for
    that reason, not because attrs was missing it.

    Args:
        instance: The attrs instance being pickled.
        overrides: Field name to replacement value, for fields (e.g. a live
            connection, an in-memory cache, a lock) whose pickled state must
            be reset rather than carried over as-is.
    """
    state = {f.name: getattr(instance, f.name) for f in fields(type(instance))}
    state.update(overrides)
    return state


def attrs_setstate(instance: AttrsInstance, state: dict[str, Any]) -> None:
    """Restore attrs instance state from `attrs_getstate`, bypassing `on_setattr` hooks.

    Restoring exact prior state is not a semantic mutation those hooks
    should react to, and some fields' hooks may assume other fields are
    already set — an order-of-restoration hazard plain `setattr` would risk.
    Mirrors attrs' own auto-generated `__setstate__` for slotted classes,
    which restores via `object.__setattr__` for the identical reason — see
    [`attrs_getstate`][pysmo._utils.attrs_getstate] for why that
    auto-generated version can't be reused directly here.
    """
    for name, value in state.items():
        object.__setattr__(instance, name, value)
