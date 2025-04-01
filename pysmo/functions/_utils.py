"""Functions for 'Mini' classes."""

from pysmo.lib.typing import _AnyProto, _AnyMini
from attrs import fields
from copy import copy
from typing import cast


__all__ = [
    "copy_from_mini",
    "clone_to_mini",
]


def copy_from_mini(source: _AnyMini, target: _AnyProto) -> None:
    """Copy attributes from a Mini instance to matching other one.

    This function [copies][copy.copy] all attributes in the `source` Mini class
    instance to a compatible `target` instance.

    Parameters:
        source: The Mini instance to copy attributes from.
        target: Compatible target instance.

    Raises:
        AttributeError: If the `target` instance does not contain all
            attributes in the `source` instance.

    See Also:
        [`clone_to_mini`][pysmo.functions.clone_to_mini]: Create a new
        instance of a Mini class from a matching other one.
    """

    if all(map(lambda x: hasattr(target, x.name), fields(type(source)))):
        for attr in fields(type(source)):
            setattr(target, attr.name, copy(getattr(source, attr.name)))
    else:
        raise AttributeError(
            f"Unable to copy to target: {type(target)} not compatible with {type(source)}."
        )


def clone_to_mini[TMini: _AnyMini](mini_cls: type[TMini], source: _AnyProto) -> TMini:
    """Create a new instance of a Mini class from a matching other one.

    This function is creates a clone of an exising class by
    [copying][copy.copy] the attributes defined in `mini_cls` from the source
    to the target. Attributes only present in the source object are ignored,
    potentially resulting in a smaller and more performant object.

    Parameters:
        mini_cls: The type of Mini class to create.
        source: The instance to clone (must contain all attributes present
            in `mini_cls`).

    Returns:
        A new Mini instance type mini_cls.

    Raises:
        AttributeError: If the source instance does not contain all attributes
            in mini_cls.

    Examples:
        Create a [`MiniSeismogram`][pysmo.MiniSeismogram] from a
        [`SacSeismogram`][pysmo.classes.SacSeismogram] instance.

        >>> from pysmo.funtions import clone_to_mini
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.classes import SAC
        >>> sac_seismogram = SAC.from_file("testfile.sac").seismogram
        >>> mini_seismogram = clone_to_mini(MiniSeismogram, sac_seismogram)

    See Also:
        [`copy_from_mini`][pysmo.functions.copy_from_mini]: Copy attributes
        from a Mini instance to matching other one.
    """

    if all(map(lambda x: hasattr(source, x.name), fields(mini_cls))):
        clone_dict = {
            attr.name: copy(getattr(source, attr.name)) for attr in fields(mini_cls)
        }
        # TODO: why do we need cast here for mypy?
        return cast(TMini, mini_cls(**clone_dict))

    raise AttributeError(
        f"Unable to create clone: {source} not compatible with {mini_cls}."
    )
