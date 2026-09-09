"""Checksum a seismogram, and round-trip a value-object seismogram through JSON."""

import base64
import hashlib
import importlib
import json
import typing
from collections.abc import Hashable
from typing import Any, TypeIs, cast, overload

import attrs
import numpy as np
import numpy.typing as npt
import pandas as pd
from cattrs import Converter

from pysmo import Seismogram
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = [
    "seismogram_checksum",
    "seismogram_from_json",
    "seismogram_to_json",
]

_SEISMOGRAM_JSON_VERSION = 1
"""Envelope schema and leaf-hook version, written into every
`seismogram_to_json` document; bump on any change to the payload shape or the
leaf hooks below."""

_SEISMOGRAM_LEAVES = ("begin_time", "delta", "data")


def _unstructure_ndarray(array: npt.NDArray[Any]) -> dict[str, Any]:
    # tobytes() is C-order and copies a non-contiguous array as needed.
    return {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "b64": base64.b64encode(array.tobytes()).decode("ascii"),
    }


def _structure_ndarray(value: dict[str, Any], _: Any) -> npt.NDArray[Any]:
    raw = base64.b64decode(value["b64"])
    # .copy() so the reconstructed array is writable, not a read-only buffer view.
    return np.frombuffer(raw, dtype=value["dtype"]).reshape(value["shape"]).copy()


def _is_ndarray_type(candidate: Any) -> bool:
    return candidate is np.ndarray or typing.get_origin(candidate) is np.ndarray


def _is_extra_type(candidate: Any) -> bool:
    return candidate == dict[Hashable, Any]


def _make_converter() -> Converter:
    """A `cattrs` converter that round-trips a value-object seismogram through JSON.

    Handles the three leaf types a [`Seismogram`][pysmo.Seismogram] carries
    (`pd.Timestamp`, `pd.Timedelta`, `np.ndarray`) plus the untyped `extra`
    mapping on [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram].
    """
    converter = Converter()
    converter.register_unstructure_hook(pd.Timestamp, lambda ts: ts.value)
    converter.register_structure_hook(
        pd.Timestamp, lambda v, _: convert_to_utc_timestamp(pd.Timestamp(v))
    )
    converter.register_unstructure_hook(pd.Timedelta, lambda td: td.value)
    converter.register_structure_hook(pd.Timedelta, lambda v, _: pd.Timedelta(v))
    converter.register_unstructure_hook_func(_is_ndarray_type, _unstructure_ndarray)
    converter.register_structure_hook_func(_is_ndarray_type, _structure_ndarray)
    converter.register_unstructure_hook_func(_is_extra_type, dict)
    converter.register_structure_hook_func(_is_extra_type, lambda v, _: dict(v))
    return converter


_converter = _make_converter()


def seismogram_checksum(seismogram: Seismogram) -> str:
    """Return a stable digest of a seismogram's samples and timing.

    Covers `data`, `begin_time`, and `delta`, the three members of the
    [`Seismogram`][pysmo.Seismogram] protocol, and nothing else: two
    seismograms with equal values for those hash the same regardless of their
    concrete type or any extra attributes it carries. The result is prefixed
    with the hash name (`sha256:`).

    Examples:
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.functions import seismogram_checksum
        >>>
        >>> seismogram = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2024-01-01T00:00:00Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=[1.0, 2.0, 3.0],
        ... )
        >>> seismogram_checksum(seismogram)
        'sha256:...'
        >>> rebuilt = MiniSeismogram(
        ...     begin_time=seismogram.begin_time,
        ...     delta=seismogram.delta,
        ...     data=[1.0, 2.0, 3.0],
        ... )
        >>> seismogram_checksum(rebuilt) == seismogram_checksum(seismogram)
        True
        >>>
    """
    h = hashlib.sha256()
    h.update(seismogram.data.tobytes())
    # `.value` (integer nanoseconds) rather than `str()`: a fixed
    # representation that does not shift with the pandas version.
    h.update(str(seismogram.begin_time.value).encode())
    h.update(str(seismogram.delta.value).encode())
    return f"sha256:{h.hexdigest()}"


def _is_serializable_seismogram(obj: object) -> TypeIs[Seismogram]:
    """Whether `obj` is an attrs seismogram `seismogram_to_json` can encode.

    True only for an `attrs` class that declares `begin_time`, `delta`, and
    `data` as real fields (not property-backed protocol members, as
    `SacSeismogram` does over its `SacIO` parent), each holding the expected
    leaf type.
    """
    cls = type(obj)
    if not attrs.has(cls):
        return False
    if not set(_SEISMOGRAM_LEAVES) <= {f.name for f in attrs.fields(cls)}:
        return False
    return (
        isinstance(getattr(obj, "begin_time"), pd.Timestamp)
        and isinstance(getattr(obj, "delta"), pd.Timedelta)
        and isinstance(getattr(obj, "data"), np.ndarray)
    )


def seismogram_to_json(seismogram: Seismogram, *, verify: bool = False) -> bytes:
    """Encode a value-object seismogram as a portable JSON document.

    The document is a `{"cls", "v", "payload"}` envelope: `cls` records the
    seismogram's `module:qualname` so
    [`seismogram_from_json`][pysmo.functions.seismogram_from_json] can rebuild
    the same type, `v` is the codec version, and `payload` holds the
    seismogram's fields with `pd.Timestamp` and `pd.Timedelta` as integer
    nanoseconds and `np.ndarray` as a base64 `dtype`/`shape`/`b64` triple.

    Note: Not every seismogram can be encoded
        Only an `attrs` value object declaring `begin_time`, `delta` and
        `data` as real fields round-trips:
        [`MiniSeismogram`][pysmo.MiniSeismogram],
        [`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram],
        [`GeoCsvSeismogram`][pysmo.classes.GeoCsvSeismogram], and user types
        built the same way. A live view such as
        [`SacSeismogram`][pysmo.classes.SacSeismogram], or a type carrying a
        field the codec has no hook for, raises `TypeError`; convert it with
        [`clone_to_mini`][pysmo.functions.clone_to_mini] first.

    Args:
        seismogram: The seismogram to encode.
        verify: Decode the fresh document and compare it back to `seismogram`,
            raising `TypeError` on any mismatch. Catches a codec that silently
            drops information on a rich field (a non-primitive value in
            [`MiniIccsSeismogram.extra`][pysmo.tools.iccs.MiniIccsSeismogram],
            say).

    Returns:
        The UTF-8 JSON document.

    Raises:
        TypeError: If `seismogram` is not a serialisable attrs seismogram, a
            field has no `cattrs` hook, or `verify` is set and the document
            does not round-trip.

    Examples:
        >>> import json
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.functions import seismogram_from_json, seismogram_to_json
        >>>
        >>> seismogram = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2024-01-01T00:00:00Z"),
        ...     delta=pd.Timedelta(seconds=1),
        ...     data=[1.0, 2.0, 3.0],
        ... )
        >>> blob = seismogram_to_json(seismogram)
        >>> json.loads(blob)
        {'cls': 'pysmo:MiniSeismogram', 'v': 1,
         'payload': {'begin_time': 1704067200000000000, 'delta': 1000000000,
                     'data': {'dtype': 'float64', 'shape': [3],
                              'b64': 'AAAAAAAA8D8AAAAAAAAAQAAAAAAAAAhA'}}}
        >>> seismogram_from_json(blob) == seismogram
        True
        >>>
    """
    if not _is_serializable_seismogram(seismogram):
        raise TypeError(
            f"{type(seismogram).__name__} cannot be serialised: it is not an "
            + "attrs seismogram declaring begin_time/delta/data as real fields. "
            + "Convert it with clone_to_mini first."
        )
    try:
        envelope = {
            "cls": f"{type(seismogram).__module__}:{type(seismogram).__qualname__}",
            "v": _SEISMOGRAM_JSON_VERSION,
            "payload": _converter.unstructure(seismogram),
        }
        blob = json.dumps(envelope).encode("utf-8")
    except Exception as exc:
        raise TypeError(
            f"{type(seismogram).__name__} has a field the seismogram codec "
            + f"cannot serialise ({exc}); register a hook on a custom converter, "
            + "or convert it with clone_to_mini first."
        ) from exc
    if verify:
        try:
            matches = seismogram_from_json(blob) == seismogram
        except Exception as exc:
            raise TypeError(
                f"{type(seismogram).__name__} does not survive a JSON round trip "
                + f"({exc}); a codec hook is lossy for one of its fields."
            ) from exc
        if matches is not True:
            raise TypeError(
                f"{type(seismogram).__name__} does not survive a JSON round trip "
                + "(decoded value differs); a codec hook is lossy for one of its "
                + "fields."
            )
    return blob


@overload
def seismogram_from_json(blob: bytes, cls: None = ...) -> Seismogram: ...


@overload
def seismogram_from_json[T: Seismogram](blob: bytes, cls: type[T]) -> T: ...


def seismogram_from_json(
    blob: bytes, cls: type[Seismogram] | None = None
) -> Seismogram:
    """Reconstruct a seismogram from a `seismogram_to_json` document.

    Args:
        blob: The document produced by
            [`seismogram_to_json`][pysmo.functions.seismogram_to_json].
        cls: The attrs class to rebuild, returned as its own type. When
            `None`, the `module:qualname` recorded in the document is
            imported and the result is typed as
            [`Seismogram`][pysmo.Seismogram]; pass `cls` explicitly when the
            type may have moved since it was encoded, or to keep the concrete
            return type.

    Returns:
        A new instance of `cls`, or of the recorded type.

    Raises:
        TypeError: If `cls` is `None` and the recorded type can no longer be
            imported, or the resolved type is not an attrs class.

    Examples:
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.functions import seismogram_from_json, seismogram_to_json
        >>>
        >>> blob = seismogram_to_json(
        ...     MiniSeismogram(
        ...         begin_time=pd.Timestamp("2024-01-01T00:00:00Z"),
        ...         delta=pd.Timedelta(seconds=1),
        ...         data=[1.0, 2.0, 3.0],
        ...     )
        ... )
        >>> seismogram_from_json(blob, cls=MiniSeismogram).data.tolist()
        [1.0, 2.0, 3.0]
        >>>
    """
    envelope = json.loads(blob)
    resolved: type[Seismogram]
    if cls is None:
        name: str = envelope["cls"]
        module_name, _, qualname = name.partition(":")
        try:
            obj: Any = importlib.import_module(module_name)
            for part in qualname.split("."):
                obj = getattr(obj, part)
        except (ImportError, AttributeError) as exc:
            raise TypeError(
                f"Encoded class {name!r} can no longer be imported ({exc}); the "
                + "type moved or was removed. Pass an explicit cls, or re-encode "
                + "from scratch."
            ) from exc
        resolved = obj
    else:
        resolved = cls
    if not attrs.has(resolved):
        raise TypeError(f"{resolved!r} is not an attrs class.")
    return cast(Seismogram, _converter.structure(envelope["payload"], resolved))
