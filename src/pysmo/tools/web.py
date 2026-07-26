"""Tools for fetching seismological data from web services."""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Self

import pandas as pd

from pysmo import Event, Station
from pysmo.classes import GeoCsvSeismogram
from pysmo.lib.io import http_get
from pysmo.lib.validators import convert_to_utc_timestamp
from pysmo.tools.azdist import haversine

__all__ = ["TravelTimeBackend", "fetch_seismogram", "fetch_travel_times"]

type TravelTimeBackend = Callable[[float, float, list[str]], dict[str, float]]
"""Callable `(depth_km, dist_deg, phases) -> dict[str, float]` returning travel times.

Accepts source depth in kilometres, epicentral distance in degrees, and a list of
seismic phase names (e.g. `["P", "S"]`). Returns a mapping of phase name to
travel time in seconds, omitting phases with no arrival at the given geometry.
Keys must match the requested phase names verbatim; `fetch_seismogram` raises
`ValueError` if none of the requested phases appear in the returned mapping.
"""


@dataclass(init=False)
class _EarthScopeDefaults:
    def __new__(cls) -> Self:
        raise RuntimeError(
            "_EarthScopeDefaults is not meant to be instantiated. "
            "Use _EarthScopeDefaults.<attribute> instead."
        )

    dataselect_url: str = "https://service.earthscope.org/fdsnws/dataselect/1/query"
    traveltime_url: str = "https://service.earthscope.org/irisws/traveltime/1/query"
    timeout_seconds: int = 30
    request_retries: int = 3
    retry_delay_seconds: int = 20


def fetch_seismogram(
    *,
    station: Station,
    event: Event | None = None,
    starttime: pd.Timestamp | None = None,
    endtime: pd.Timestamp | None = None,
    pre: pd.Timedelta | None = None,
    post: pd.Timedelta | None = None,
    phases: list[str] | None = None,
    model: str = "iasp91",
    travel_time_backend: TravelTimeBackend | None = None,
) -> tuple[GeoCsvSeismogram, dict[str, pd.Timestamp]]:
    """Fetch a seismogram from the EarthScope FDSN dataselect web service.

    Provide either an absolute time window (*starttime* + *endtime*) or a
    phase-relative window (*pre* + *post*). The phase-relative option
    requires *event* so that the predicted arrival time can be computed.

    The returned [`GeoCsvSeismogram`][pysmo.classes.GeoCsvSeismogram] can be
    converted to other seismogram types with
    [`clone_to_mini`][pysmo.functions.clone_to_mini] and
    [`copy_from_mini`][pysmo.functions.copy_from_mini].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location,
            channel, and coordinates for the request.
        event: Any object satisfying the [`Event`][pysmo.Event] protocol.
            Required for phase-relative windows; optional (but recommended)
            for absolute windows as it enables computation of the predicted
            arrivals.
        starttime: Start of the requested time window (UTC). Use with
            *endtime* for an absolute window.
        endtime: End of the requested time window (UTC). Use with
            *starttime* for an absolute window.
        pre: Duration before the predicted arrival to include. Use with
            *post* for a phase-relative window.
        post: Duration after the predicted arrival to include. Use with
            *pre* for a phase-relative window.
        phases: Seismic phases to compute travel times for. If `None`,
            uses `["P"]`. The first phase found in this list anchors the
            phase-relative window.
        model: Velocity model name passed to the EarthScope traveltime
            service (or *travel_time_backend*).
        travel_time_backend: Optional callable that overrides the EarthScope
            traveltime web service. Must accept
            `(depth_km, dist_deg, phases)` and return a mapping of
            phase name to travel time in seconds. See
            [`TravelTimeBackend`][pysmo.tools.web.TravelTimeBackend].

    Returns:
        seismogram: The fetched waveform.
        predicted_arrivals: Predicted phase arrival times as absolute UTC
            timestamps, keyed by phase name (e.g. `{"P": Timestamp(...)}`).
            Empty when no *event* was provided. For an absolute window
            (*starttime* + *endtime*), computing these is a best-effort
            enrichment performed after the waveform has already been
            fetched: if it fails for any reason (including a web-service
            error), a `UserWarning` is raised and *predicted_arrivals* is
            empty, but the fetched *seismogram* is still returned. For a
            phase-relative window (*pre* + *post*), predicted arrivals are
            required to compute the window and failures raise instead (see
            *Raises*).

    Raises:
        ValueError: If the time-window arguments are inconsistent, no
            waveform data is returned, a data gap prevents merging
            segments into a continuous trace, or (for a phase-relative
            window) none of the requested *phases* are found in the
            travel-time response.
        urllib3.exceptions.ResponseError: If the dataselect web service
            returns an HTTP error, or (for a phase-relative window) the
            traveltime web service does.

    Examples:
        Fetch a 10-minute window around the predicted P arrival for the
        2010 Maule earthquake recorded at IU.ANMO:

        ```python
        >>> import pandas as pd
        >>> from pysmo import MiniEvent, MiniStation
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> event = MiniEvent(
        ...     latitude=-36.122, longitude=-72.898, depth=22900.0,
        ...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
        ... )
        >>> seismogram, arrivals = fetch_seismogram(  # doctest: +SKIP
        ...     station=station,
        ...     event=event,
        ...     pre=pd.Timedelta(minutes=2),
        ...     post=pd.Timedelta(minutes=8),
        ... )
        >>>
        ```
    """
    if phases is None:
        phases = ["P"]

    has_starttime = starttime is not None
    has_endtime = endtime is not None
    has_pre = pre is not None
    has_post = post is not None
    has_absolute = has_starttime and has_endtime
    has_relative = has_pre and has_post

    if has_starttime != has_endtime:
        raise ValueError("Provide both starttime and endtime, or neither.")
    if has_pre != has_post:
        raise ValueError("Provide both pre and post, or neither.")
    if has_absolute == has_relative:
        raise ValueError(
            "Provide either (starttime and endtime) or (pre and post), "
            "not both or neither."
        )
    if has_relative and event is None:
        raise ValueError("event is required when using pre and post.")

    travel_times: dict[str, float] = {}

    if has_relative:
        assert event is not None  # validated above
        assert pre is not None
        assert post is not None
        dist = haversine(event, station)
        travel_times = fetch_travel_times(
            event.depth / 1000.0, dist, phases, model, travel_time_backend
        )
        if not travel_times:
            raise ValueError(
                f"No arrivals found for phases {phases!r} at "
                f"distance {dist:.2f}° and depth {event.depth / 1000:.1f} km."
            )
        first_phase = next((p for p in phases if p in travel_times), None)
        if first_phase is None:
            raise ValueError(
                f"None of the requested phases {phases!r} were found in "
                f"travel times: {list(travel_times.keys())}."
            )
        predicted = event.time + pd.Timedelta(seconds=travel_times[first_phase])
        starttime = predicted - pre
        endtime = predicted + post

    assert starttime is not None
    assert endtime is not None

    starttime = convert_to_utc_timestamp(starttime)
    endtime = convert_to_utc_timestamp(endtime)

    waveform_bytes = http_get(
        _EarthScopeDefaults.dataselect_url,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "starttime": starttime.isoformat(),
            "endtime": endtime.isoformat(),
            "format": "geocsv",
        },
        timeout_seconds=_EarthScopeDefaults.timeout_seconds,
        request_retries=_EarthScopeDefaults.request_retries,
        retry_delay_seconds=_EarthScopeDefaults.retry_delay_seconds,
    )
    if not waveform_bytes.strip():
        raise ValueError(
            f"No waveform data returned for "
            f"{station.network}.{station.name}.{station.location}.{station.channel} "
            f"between {starttime} and {endtime}."
        )

    seismogram = GeoCsvSeismogram.from_text(waveform_bytes.decode("utf-8"))

    if event is not None and not travel_times:
        dist = haversine(event, station)
        try:
            travel_times = fetch_travel_times(
                event.depth / 1000.0, dist, phases, model, travel_time_backend
            )
        except Exception as error:
            # Predicted arrivals are a best-effort enrichment here (an absolute
            # window was given, so they aren't required to fetch the waveform);
            # a failure must not discard the seismogram already fetched above.
            warnings.warn(
                f"Could not compute predicted arrivals: {error}",
                UserWarning,
                stacklevel=2,
            )

    predicted_arrivals = (
        {
            phase: event.time + pd.Timedelta(seconds=t)
            for phase, t in travel_times.items()
        }
        if event is not None
        else {}
    )

    return seismogram, predicted_arrivals


def fetch_travel_times(
    depth_km: float,
    dist_deg: float,
    phases: list[str],
    model: str = "iasp91",
    travel_time_backend: TravelTimeBackend | None = None,
) -> dict[str, float]:
    """Fetch seismic phase travel times for a given source–receiver geometry.

    Uses the EarthScope traveltime web service by default, or a custom
    callable if *travel_time_backend* is provided.

    Args:
        depth_km: Source depth in kilometres.
        dist_deg: Epicentral distance in degrees.
        phases: Seismic phase names to request (e.g. `["P", "S"]`).
        model: Velocity model name.
        travel_time_backend: Optional callable overriding the web service. Must
            accept `(depth_km, dist_deg, phases)` and return a mapping of
            phase name to travel time in seconds. See
            [`TravelTimeBackend`][pysmo.tools.web.TravelTimeBackend].

    Returns:
        Mapping of phase name to travel time in seconds. Only phases with
        arrivals at the given distance and depth are included.

    Examples:
        Using a custom `travel_time_backend` instead of the EarthScope web service.
        The lambda below is a stand-in; replace it with a real travel-time
        calculator:

        ```python
        >>> from pysmo.tools.web import fetch_travel_times
        >>> backend = lambda depth, dist, phases: {"P": 480.2, "S": 900.1}
        >>> fetch_travel_times(22.9, 60.0, ["P", "S"], travel_time_backend=backend)
        {'P': 480.2, 'S': 900.1}
        >>>
        ```
    """
    if travel_time_backend is not None:
        return travel_time_backend(depth_km, dist_deg, phases)
    data = http_get(
        _EarthScopeDefaults.traveltime_url,
        {
            "model": model,
            "evdepth": depth_km,
            "distdeg": dist_deg,
            "phases": ",".join(phases),
            "format": "json",
        },
        timeout_seconds=_EarthScopeDefaults.timeout_seconds,
        request_retries=_EarthScopeDefaults.request_retries,
        retry_delay_seconds=_EarthScopeDefaults.retry_delay_seconds,
    )
    result: dict[str, Any] = json.loads(data)
    arrivals: dict[str, float] = {}
    for arr in result.get("arrivals", []):
        phase = str(arr["phase"])
        if phase not in arrivals:
            arrivals[phase] = float(arr["time"])
    return arrivals
