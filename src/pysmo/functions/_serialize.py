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
from pysmo.lib.converters import to_utc_timestamp

__all__ = [
    "seismogram_checksum",
    "seismogram_from_json",
    "seismogram_to_json",
]

_SEISMOGRAM_JSON_VERSION = 1
"""Envelope schema and leaf-hook version, written into every
`seismogram_to_json` document; bump on any change to the payload shape or the
leaf hooks below."""

_SUPPORTED_JSON_VERSIONS = frozenset({1})
"""Envelope versions `seismogram_from_json` will decode."""

_DEFAULT_TRUSTED_MODULES = ("pysmo",)
"""Top-level packages `seismogram_from_json` will import a recorded class from
when no explicit `cls` is passed. Anything else needs `cls`, so a tampered
document cannot name an arbitrary importable module."""

_SEISMOGRAM_LEAVES = ("begin_time", "delta", "data")

_NUMERIC_DTYPE_KINDS = frozenset("biufc")
"""ndarray dtype kinds the codec will reconstruct: bool, signed/unsigned int,
float, complex. Excludes object, void and string, which reinterpret arbitrary
bytes."""


def _unstructure_ndarray(array: npt.NDArray[Any]) -> dict[str, Any]:
    # tobytes() is C-order and copies a non-contiguous array as needed.
    return {
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "b64": base64.b64encode(array.tobytes()).decode("ascii"),
    }


def _structure_ndarray(value: dict[str, Any], _: Any) -> npt.NDArray[Any]:
    dtype = np.dtype(value["dtype"])
    if dtype.hasobject or dtype.kind not in _NUMERIC_DTYPE_KINDS:
        raise ValueError(f"unsupported ndarray dtype {value['dtype']!r}")
    raw = base64.b64decode(value["b64"])
    # .copy() so the reconstructed array is writable, not a read-only buffer view.
    return np.frombuffer(raw, dtype=dtype).reshape(value["shape"]).copy()


def _is_ndarray_type(candidate: Any) -> bool:
    return candidate is np.ndarray or typing.get_origin(candidate) is np.ndarray


def _is_extra_type(candidate: Any) -> bool:
    return candidate == dict[Hashable, Any]


def _make_converter() -> Converter:
    """A `cattrs` converter that round-trips a value-object seismogram through JSON.

    Handles the three leaf types a [`Seismogram`][pysmo.Seismogram] carries
    (`pd.Timestamp`, `pd.Timedelta`, `np.ndarray`) plus an untyped
    `dict[Hashable, Any]` mapping, which is passed through shallowly: keys and
    values must already be JSON primitives, lists, or nested dicts of the same.
    """
    converter = Converter()
    converter.register_unstructure_hook(pd.Timestamp, lambda ts: ts.value)
    converter.register_structure_hook(
        pd.Timestamp, lambda v, _: to_utc_timestamp(pd.Timestamp(v))
    )
    converter.register_unstructure_hook(pd.Timedelta, lambda td: td.value)
    converter.register_structure_hook(pd.Timedelta, lambda v, _: pd.Timedelta(v))
    converter.register_unstructure_hook_func(_is_ndarray_type, _unstructure_ndarray)
    converter.register_structure_hook_func(_is_ndarray_type, _structure_ndarray)
    converter.register_unstructure_hook_func(_is_extra_type, dict)
    converter.register_structure_hook_func(_is_extra_type, lambda v, _: dict(v))
    return converter


_converter = _make_converter()


def _hash_field(h: Any, name: bytes, value: bytes) -> None:
    """Feed a length-prefixed, name-tagged field into a hash.

    The length prefix and name tag keep concatenated fields from being
    rearranged into a colliding byte stream.
    """
    h.update(name)
    h.update(len(value).to_bytes(8, "big"))
    h.update(value)


def _int64(value: int) -> bytes:
    return int(value).to_bytes(8, "big", signed=True)


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
    data = np.ascontiguousarray(seismogram.data)
    _hash_field(h, b"dtype", data.dtype.str.encode())
    _hash_field(h, b"shape", repr(tuple(int(n) for n in data.shape)).encode())
    _hash_field(h, b"data", data.tobytes())
    # `.value` (integer nanoseconds) rather than `str()`: a fixed
    # representation that does not shift with the pandas version.
    _hash_field(h, b"begin_time", _int64(seismogram.begin_time.value))
    _hash_field(h, b"delta", _int64(seismogram.delta.value))
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
            say). `data` is compared with `equal_nan`, so a genuine `NaN`
            sample (a data gap, a masked window) is not reported as a lossy
            round trip.

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
    except MemoryError:
        raise
    except Exception as exc:
        raise TypeError(
            f"{type(seismogram).__name__} has a field the seismogram codec "
            + f"cannot serialise ({exc}); register a hook on a custom converter, "
            + "or convert it with clone_to_mini first."
        ) from exc
    if verify:
        try:
            restored = seismogram_from_json(blob, cls=type(seismogram))
        except MemoryError:
            raise
        except Exception as exc:
            raise TypeError(
                f"{type(seismogram).__name__} does not survive a JSON round trip "
                + f"({exc}); a codec hook is lossy for one of its fields."
            ) from exc
        if not _round_trip_faithful(restored, seismogram):
            raise TypeError(
                f"{type(seismogram).__name__} does not survive a JSON round trip "
                + "(decoded value differs); a codec hook is lossy for one of its "
                + "fields."
            )
    return blob


def _round_trip_faithful(restored: object, original: Seismogram) -> bool:
    """Whether every field of `restored` matches `original`.

    `data` is compared with `equal_nan` so a real `NaN` sample is not a false
    "lossy hook" report; every other field with plain equality, so a hook that
    changes a value's type (a tuple decoded as a list) is still caught.
    """
    cls = type(original)
    if type(restored) is not cls or not attrs.has(cls):
        return False
    for f in attrs.fields(cls):
        left = getattr(restored, f.name)
        right = getattr(original, f.name)
        if isinstance(right, np.ndarray):
            equal_nan = np.issubdtype(right.dtype, np.inexact)
            if not np.array_equal(left, right, equal_nan=bool(equal_nan)):
                return False
        elif (left == right) is not True:
            return False
    return True


@overload
def seismogram_from_json(
    blob: bytes, cls: None = ..., *, trusted_modules: tuple[str, ...] = ...
) -> Seismogram: ...


@overload
def seismogram_from_json[T: Seismogram](
    blob: bytes, cls: type[T], *, trusted_modules: tuple[str, ...] = ...
) -> T: ...


def seismogram_from_json(
    blob: bytes,
    cls: type[Seismogram] | None = None,
    *,
    trusted_modules: tuple[str, ...] = _DEFAULT_TRUSTED_MODULES,
) -> Seismogram:
    """Reconstruct a seismogram from a `seismogram_to_json` document.

    The document is data, not code: no part of it is executed. When `cls` is
    `None` the recorded `module:qualname` is imported to rebuild the type, but
    only from a package in `trusted_modules` — a tampered document cannot name
    an arbitrary importable module to trigger its import side effects.

    Args:
        blob: The document produced by
            [`seismogram_to_json`][pysmo.functions.seismogram_to_json].
        cls: The attrs class to rebuild, returned as its own type. When
            `None`, the `module:qualname` recorded in the document is
            imported and the result is typed as
            [`Seismogram`][pysmo.Seismogram]; pass `cls` explicitly when the
            type may have moved since it was encoded, to keep the concrete
            return type, or to rebuild a type from outside `trusted_modules`.
        trusted_modules: Top-level packages the recorded class may be imported
            from when `cls` is `None`. Defaults to pysmo's own types only.

    Returns:
        A new instance of `cls`, or of the recorded type.

    Raises:
        TypeError: If the document is malformed or an unsupported version, if
            `cls` is `None` and the recorded module is not trusted or can no
            longer be imported, if the resolved type is not an attrs class, or
            if the payload does not fit the resolved type.

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
    try:
        envelope = json.loads(blob)
    except (ValueError, TypeError) as exc:
        raise TypeError(f"not a valid seismogram JSON document ({exc}).") from exc
    if not isinstance(envelope, dict) or not {"cls", "v", "payload"} <= envelope.keys():
        raise TypeError(
            "seismogram JSON document is missing its cls/v/payload envelope."
        )
    version = envelope["v"]
    if not isinstance(version, int) or version not in _SUPPORTED_JSON_VERSIONS:
        raise TypeError(
            f"seismogram JSON document is version {version!r}; this pysmo reads "
            + f"{sorted(_SUPPORTED_JSON_VERSIONS)}."
        )

    resolved: type[Seismogram]
    if cls is None:
        resolved = _resolve_encoded_class(envelope["cls"], trusted_modules)
    else:
        resolved = cls
    if not attrs.has(resolved):
        raise TypeError(f"{resolved!r} is not an attrs class.")
    try:
        return cast(Seismogram, _converter.structure(envelope["payload"], resolved))
    except MemoryError:
        raise
    except Exception as exc:
        raise TypeError(
            f"seismogram JSON payload does not fit {resolved!r} ({exc})."
        ) from exc


def _resolve_encoded_class(
    name: object, trusted_modules: tuple[str, ...]
) -> type[Seismogram]:
    if not isinstance(name, str) or ":" not in name:
        raise TypeError(f"encoded class {name!r} is not a 'module:qualname' string.")
    module_name, _, qualname = name.partition(":")
    if module_name.split(".", 1)[0] not in trusted_modules:
        raise TypeError(
            f"refusing to import encoded class {name!r}: {module_name!r} is not in "
            + f"the trusted set {list(trusted_modules)}. Pass an explicit cls to "
            + "rebuild a type from another package."
        )
    try:
        obj: Any = importlib.import_module(module_name)
        for part in qualname.split("."):
            obj = getattr(obj, part)
    except (ImportError, AttributeError) as exc:
        raise TypeError(
            f"encoded class {name!r} can no longer be imported ({exc}); the type "
            + "moved or was removed. Pass an explicit cls, or re-encode from scratch."
        ) from exc
    return cast(type[Seismogram], obj)
