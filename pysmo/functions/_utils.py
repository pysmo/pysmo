"""Functions for 'Mini' classes."""

from attrs import fields, NOTHING
from cattrs import unstructure
from copy import copy
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pysmo.lib.typing import _AnyProto, _AnyMini

__all__ = [
    "copy_from_mini",
    "clone_to_mini",
]


def copy_from_mini(
    source: "_AnyMini", target: "_AnyProto", update: dict | None = None
) -> None:
    """Copy attributes from a Mini instance to matching other one.

    This function [copies][copy.copy] all attributes in the `source` Mini class
    instance to a compatible `target` instance.

    Parameters:
        source: The Mini instance to copy attributes from.
        target: Compatible target instance.
        update: Update or add attributes in the target instance.

    Raises:
        AttributeError: If the `target` instance does not contain all
            attributes in the `source` instance (unless they are
            provided with the `update` keyword argument).

    Tip: See Also
        [`clone_to_mini`][pysmo.functions.clone_to_mini]: Create a new
        instance of a Mini class from a matching other one.
    """

    update = update or dict()

    attributes = unstructure(source).keys() | set()
    attributes.update(update.keys())

    if all(map(lambda x: hasattr(target, x), attributes)):
        for attribute in attributes:
            if attribute in update:
                setattr(target, attribute, update[attribute])
            else:
                setattr(target, attribute, copy(getattr(source, attribute)))
    else:
        raise AttributeError(
            f"Unable to copy to target: {type(target)} not compatible with {type(source)}."
        )


def clone_to_mini[TMini: _AnyMini](
    mini_cls: type[TMini], source: "_AnyProto", update: dict | None = None
) -> TMini:
    """Create a new instance of a Mini class from a matching other one.

    This function is creates a clone of an exising class by
    [copying][copy.copy] the attributes defined in `mini_cls` from the source
    to the target. Attributes only present in the source object are ignored,
    potentially resulting in a smaller and more performant object.

    If the source instance is missing an attribute for which a default is
    defined in the target class, then that default value for that attribute is
    used.

    Parameters:
        mini_cls: The type of Mini class to create.
        source: The instance to clone (must contain all attributes present
            in `mini_cls`).
        update: Update or add attributes in the returned `mini_cls` instance.

    Returns:
        A new Mini instance type mini_cls.

    Raises:
        AttributeError: If the `source` instance does not contain all
            attributes in `mini_cls` (unless they are provided with the
            `update` keyword argument).

    Examples:
        Create a [`MiniSeismogram`][pysmo.MiniSeismogram] from a
        [`SacSeismogram`][pysmo.classes.SacSeismogram] instance with
        a new `begin_time`.

        ```python
        >>> from pysmo.functions import clone_to_mini
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.classes import SAC
        >>> from datetime import datetime, timezone
        >>> now = datetime.now(timezone.utc)
        >>> sac_seismogram = SAC.from_file("example.sac").seismogram
        >>> mini_seismogram = clone_to_mini(MiniSeismogram, sac_seismogram, update={"begin_time": now})
        >>> all(sac_seismogram.data == mini_seismogram.data)
        True
        >>> mini_seismogram.begin_time == now
        True
        >>>
        ```

    Tip: See Also
        [`copy_from_mini`][pysmo.functions.copy_from_mini]: Copy attributes
        from a Mini instance to matching other one.
    """

    update = update or dict()

    if all(
        map(
            lambda x: hasattr(source, x.name)
            or x.name in update
            or x.default is not NOTHING,
            fields(mini_cls),
        )
    ):
        clone_dict = {
            attr.name: (
                update[attr.name]
                if attr.name in update
                else copy(getattr(source, attr.name, attr.default))
            )
            for attr in fields(mini_cls)
        }
        # TODO: why do we need cast here for mypy?
        return cast(TMini, mini_cls(**clone_dict))

    raise AttributeError(
        f"Unable to create clone: {source} not compatible with {mini_cls}."
    )
