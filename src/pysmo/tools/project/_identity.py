"""Precision constants, normalisation, canonical serialisation, and digests for project entry identity."""

from __future__ import annotations

import functools
import hashlib
import json
import os
from typing import TYPE_CHECKING, Any

import attrs
import pandas as pd

from pysmo import Event, Station

if TYPE_CHECKING:
    from typing import Protocol

    class _IdentityEntry(Protocol):
        """The `ProjectEntry` attributes `entry_identity` reads."""

        @property
        def station(self) -> Station: ...
        @property
        def event(self) -> Event | None: ...
        @property
        def starttime(self) -> pd.Timestamp | None: ...
        @property
        def endtime(self) -> pd.Timestamp | None: ...

    class _IdentityProject(Protocol):
        """The `PysmoProject` attributes `resolution_context_digest` reads."""

        @property
        def window(self) -> Any: ...
        @property
        def seismogram_transform(self) -> Any: ...


_IDENTITY_SCHEMA = "v1"
_LATLON_DP = 4  # ~11 m at the equator
_DEPTH_QUANTUM_M = 100.0  # nearest 0.1 km


class UnknownEntryIdentity(LookupError):
    """Raised when an entry with the requested identity is not found in the project."""

    def __init__(self, identity: str) -> None:
        super().__init__(identity)
        self.identity = identity


def _no_negative_zero(x: float) -> float:
    """Fold `-0.0` to `0.0` so rounded coordinates serialise identically."""
    return x or 0.0


def _normalise_station(station: Station) -> dict[str, str]:
    """Station code fields, stripped; a blank or padded `location` becomes `''`."""
    return {
        "network": str(station.network).strip(),
        "name": str(station.name).strip(),
        "location": str(station.location).strip(),
        "channel": str(station.channel).strip(),
    }


def _normalise_event(event: Event | None) -> dict[str, Any] | None:
    """Event hypocentre and origin time; `None` when the entry has no event.

    Latitude and longitude are rounded to `_LATLON_DP` decimal places and depth to
    the nearest `_DEPTH_QUANTUM_M` metres; origin time is exact nanoseconds.
    """
    if event is None:
        return None

    lat = _no_negative_zero(round(float(event.latitude), _LATLON_DP))
    lon = _no_negative_zero(round(float(event.longitude), _LATLON_DP))
    depth_m = _no_negative_zero(
        round(float(event.depth) / _DEPTH_QUANTUM_M) * _DEPTH_QUANTUM_M
    )

    return {
        "latitude": lat,
        "longitude": lon,
        "depth_m": depth_m,
        "time_ns": event.time.value,  # integer nanoseconds since Unix epoch UTC
    }


def _normalise_window(entry: _IdentityEntry) -> dict[str, Any] | None:
    """The explicit window as integer-nanosecond bounds, or `None` if unset."""
    if entry.starttime is None or entry.endtime is None:
        return None
    return {
        "starttime_ns": entry.starttime.value,
        "endtime_ns": entry.endtime.value,
    }


def _canonical(obj: Any) -> str:
    """Serialise an object to a canonical, stable JSON string."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _prepare_json_value(val: Any) -> Any:
    """Coerce a value to a JSON-serialisable form for canonical hashing.

    `Timestamp` and `Timedelta` become integer nanoseconds, `PathLike` its string
    form, and `-0.0` is folded to `0.0`. Anything not reducible to a JSON scalar,
    list, or dict raises `TypeError`.
    """
    if isinstance(val, pd.Timestamp):
        return val.value
    if isinstance(val, pd.Timedelta):
        return val.value
    if isinstance(val, os.PathLike):
        return os.fspath(val)
    if isinstance(val, float):
        return _no_negative_zero(val)
    if isinstance(val, (str, int, bool, type(None))):
        return val
    if isinstance(val, (list, tuple)):
        return [_prepare_json_value(item) for item in val]
    if isinstance(val, dict):
        return {str(k): _prepare_json_value(v) for k, v in val.items()}
    raise TypeError(
        f"Value {val!r} of type {type(val)} is not a supported scalar, Timestamp, "
        + "Timedelta, or PathLike."
    )


def entry_identity_components(entry: _IdentityEntry) -> dict[str, Any]:
    """The normalised natural key of an entry as a nested dict, before hashing.

    Top-level keys are `schema`, `station`, `event`, and `window`; `event` and
    `window` are `None` when absent.
    """
    return {
        "schema": _IDENTITY_SCHEMA,
        "station": _normalise_station(entry.station),
        "event": _normalise_event(entry.event),
        "window": _normalise_window(entry),
    }


def entry_identity(entry: _IdentityEntry) -> str:
    """The entry's stable identity, computed from its natural key without I/O.

    The string is `'v1:'` followed by a sha256 hexdigest.
    """
    payload = _canonical(entry_identity_components(entry))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{_IDENTITY_SCHEMA}:{digest}"


def callable_identity(fn: Any) -> str:
    """A stable, picklable identity string for a callable.

    Supports:

    - Top-level functions in importable modules.
    - `functools.partial` wrapping a supported callable.
    - `attrs` instances with picklable fields.

    Raises `TypeError` for closures, lambdas, bound methods, classes, and other
    objects.
    """
    if isinstance(fn, functools.partial):
        func_id = callable_identity(fn.func)
        args_prepared = [_prepare_json_value(arg) for arg in fn.args]
        kw_prepared = {
            k: _prepare_json_value(v) for k, v in (fn.keywords or {}).items()
        }
        payload = _canonical([args_prepared, kw_prepared])
        return f"partial:{func_id}:{payload}"

    if attrs.has(type(fn)):
        fields_payload: dict[str, Any] = {}
        for attribute in attrs.fields(type(fn)):
            value = getattr(fn, attribute.name)
            if attrs.has(type(value)) or (
                callable(value) and not isinstance(value, (str, bytes))
            ):
                # A nested callable field (e.g. a travel-time backend held as
                # a `functools.partial`) that `_prepare_json_value` cannot
                # reduce: digest it recursively instead.
                fields_payload[attribute.name] = callable_identity(value)
            else:
                fields_payload[attribute.name] = _prepare_json_value(value)
        payload = _canonical(fields_payload)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"attrs:{type(fn).__module__}:{type(fn).__qualname__}:{digest}"

    if callable(fn):
        if isinstance(fn, type):
            raise TypeError(
                f"Callable {fn!r} must be a top-level function, functools.partial, "
                + "or an attrs instance. Classes are not supported."
            )
        if hasattr(fn, "__self__"):
            raise TypeError(
                f"Callable {fn!r} is a bound method. Only top-level functions, "
                + "functools.partial, or attrs instances are supported."
            )
        qualname = getattr(fn, "__qualname__", None)
        module = getattr(fn, "__module__", None)
        if qualname is not None:
            if "<lambda>" in qualname or "<locals>" in qualname:
                raise TypeError(
                    f"Callable {fn!r} must be a top-level function, functools.partial, "
                    + "or an attrs instance. Closures and lambdas are not supported."
                )
            if module is not None:
                return f"func:{module}:{qualname}"

    raise TypeError(
        f"Callable {fn!r} of type {type(fn)} must be a top-level function, "
        + "functools.partial, or an attrs instance."
    )


def resolution_context_digest(project: _IdentityProject) -> str:
    """Digest over the project parameters that determine fetched content.

    Covers `window` and `seismogram_transform`. Reassigning `fetch_seismogram`
    (e.g. to an offline archive cache) leaves the digest unchanged.
    """
    payload = {
        "schema": "rc2",
        "window": callable_identity(project.window),
        "seismogram_transform": callable_identity(project.seismogram_transform),
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return f"rc2:{digest}"
