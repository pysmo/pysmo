"""Tools for fetching seismological data from web services.

Thin wrappers around FDSN web services (EarthScope's, except `fetch_quakeml`,
which targets USGS since EarthScope retired its event service).
`fetch_stationxml`, `fetch_station_inventory`, `fetch_sacpz`,
`fetch_geocsvseismogram`, `fetch_sac`, `fetch_mseed`, and `fetch_quakeml`
return raw, unparsed responses — most a
lower-level counterpart to a class's own parsing entry point (e.g.
[`SAC.fetch`][pysmo.classes.SAC.fetch],
[`QuakeML.all_from_bytes`][pysmo.classes.QuakeML.all_from_bytes]), useful on
their own for saving a raw response to disk and deferring parsing to later,
without another network request. `fetch_travel_times` is the exception: it
has no class counterpart and returns an already-parsed `dict[str, float]`.
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Self

import pandas as pd

from pysmo import Station
from pysmo.lib.io import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.lib.validators import convert_to_utc_timestamp

__all__ = [
    "QuakeMLOrderBy",
    "TravelTimeBackend",
    "fetch_geocsvseismogram",
    "fetch_mseed",
    "fetch_quakeml",
    "fetch_sac",
    "fetch_sacpz",
    "fetch_station_inventory",
    "fetch_stationxml",
    "fetch_travel_times",
]

type QuakeMLOrderBy = Literal["time", "time-asc", "magnitude", "magnitude-asc"]
"""Allowed `orderby` values for [`fetch_quakeml`][pysmo.tools.web.fetch_quakeml]."""

type TravelTimeBackend = Callable[[float, float, list[str]], dict[str, float]]
"""Callable `(depth_km, dist_deg, phases) -> dict[str, float]` returning travel times.

Accepts source depth in kilometres, epicentral distance in degrees, and a list of
seismic phase names (e.g. `["P", "S"]`). Returns a mapping of phase name to
travel time in seconds, omitting phases with no arrival at the given geometry.
"""


@dataclass(init=False)
class _ServiceDefaults:
    """Default web-service endpoints and HTTP retry policy.

    Mostly EarthScope's (`fdsnws-station`/`-dataselect`, `irisws-traveltime`/
    `-sacpz`); `event_url` is USGS because EarthScope retired its
    `fdsnws-event` service.
    """

    def __new__(cls) -> Self:
        raise RuntimeError(
            "_ServiceDefaults is not meant to be instantiated. "
            "Use _ServiceDefaults.<attribute> instead."
        )

    traveltime_url: str = "https://service.earthscope.org/irisws/traveltime/1/query"
    station_url: str = "https://service.earthscope.org/fdsnws/station/1/query"
    event_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    sacpz_url: str = "https://service.earthscope.org/irisws/sacpz/1/query"
    dataselect_url: str = "https://service.earthscope.org/fdsnws/dataselect/1/query"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    request_retries: int = DEFAULT_REQUEST_RETRIES
    retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS


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

        Fetching a seismogram windowed around a predicted arrival is a short
        combination of this function with [`pysmo.tools.azdist.haversine`][]
        and a class's own `.fetch()` method (e.g.
        [`GeoCsvSeismogram.fetch`][pysmo.classes.GeoCsvSeismogram.fetch], or
        [`SAC.fetch`][pysmo.classes.SAC.fetch]):

        ```python
        >>> import pandas as pd
        >>> from pysmo import MiniEvent, MiniStation
        >>> from pysmo.classes import GeoCsvSeismogram
        >>> from pysmo.tools.azdist import haversine
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> event = MiniEvent(
        ...     latitude=-36.122, longitude=-72.898, depth=22900.0,
        ...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
        ... )
        >>> dist = haversine(event, station)
        >>> backend = lambda depth, dist, phases: {"P": 604.654}  # stand-in
        >>> travel_times = fetch_travel_times(
        ...     event.depth / 1000.0, dist, ["P"], travel_time_backend=backend
        ... )
        >>> predicted_p = event.time + pd.Timedelta(seconds=travel_times["P"])
        >>>
        ```

        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> seismogram = GeoCsvSeismogram.fetch(
        ...     station=station,
        ...     starttime=predicted_p - pd.Timedelta(minutes=2),
        ...     endtime=predicted_p + pd.Timedelta(minutes=8),
        ... )
        >>>
        ```
        <!-- skip: end -->
    """
    if travel_time_backend is not None:
        return travel_time_backend(depth_km, dist_deg, phases)
    data = http_get(
        _ServiceDefaults.traveltime_url,
        {
            "model": model,
            "evdepth": depth_km,
            "distdeg": dist_deg,
            "phases": ",".join(phases),
            "format": "json",
        },
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    )
    result: dict[str, Any] = json.loads(data)
    arrivals: dict[str, float] = {}
    for arr in result.get("arrivals", []):
        phase = str(arr["phase"])
        if phase not in arrivals:
            arrivals[phase] = float(arr["time"])
    return arrivals


def fetch_stationxml(*, station: Station) -> bytes:
    """Fetch raw StationXML response metadata bytes for a station/channel.

    A lower-level counterpart to
    [`StationXML.fetch`][pysmo.classes.StationXML.fetch]: returns the
    StationXML document unparsed and uninterpreted, covering every response
    epoch on record for the requested channel. Save it to disk to defer
    parsing to later — offline, without another network request — via
    [`StationXML.from_bytes`][pysmo.classes.StationXML.from_bytes] or
    [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location, and
            channel for the request.

    Returns:
        Raw StationXML document bytes.

    Raises:
        urllib3.exceptions.ResponseError: If the station web service returns
            an HTTP error.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_stationxml
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="BHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> xml = fetch_stationxml(station=station)
        >>> _ = Path("ANMO.xml").write_bytes(xml)
        >>>
        ```
        <!-- skip: end -->
    """
    return http_get(
        _ServiceDefaults.station_url,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "level": "response",
        },
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    )


def fetch_sacpz(*, station: Station, time: pd.Timestamp | None = None) -> str:
    """Fetch raw SAC PZ response metadata text for a station/channel.

    A lower-level counterpart to
    [`SacPZ.fetch`][pysmo.classes.SacPZ.fetch]: returns the response
    metadata unparsed and uninterpreted. Save it to disk to defer parsing
    to later — offline, without another network request — via
    [`SacPZ.from_text`][pysmo.classes.SacPZ.from_text] or
    [`SacPZ.all_from_text`][pysmo.classes.SacPZ.all_from_text].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location, and
            channel for the request.
        time: Timestamp used to select the response epoch server-side, so
            exactly one epoch is returned. If `None`, the SACPZ web
            service defaults to the currently-open epoch. Truncated to
            whole seconds before the request is sent — the web service
            returns an HTTP error for a `time` with sub-second precision
            (confirmed against the live service, not documented by
            EarthScope) — with a `UserWarning` if that changes the value.

    Returns:
        Raw SAC PZ text.

    Raises:
        urllib3.exceptions.ResponseError: If the web service returns an HTTP
            error.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_sacpz
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="BHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> text = fetch_sacpz(station=station)
        >>> _ = Path("ANMO.pz").write_text(text)
        >>>
        ```
        <!-- skip: end -->
    """
    params = {
        "net": station.network,
        "sta": station.name,
        "loc": station.location,
        "cha": station.channel,
    }
    if time is not None:
        time = convert_to_utc_timestamp(time)
        floored = time.floor("s")
        if floored != time:
            warnings.warn(
                "SACPZ web service rejects sub-second precision in "
                f"'time'; truncating {time} to {floored}.",
                stacklevel=2,
            )
            time = floored
        params["time"] = time.isoformat()
    return http_get(
        _ServiceDefaults.sacpz_url,
        params,
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    ).decode("ascii")


def _fetch_dataselect(
    *,
    station: Station,
    starttime: pd.Timestamp,
    endtime: pd.Timestamp,
    response_format: str,
) -> bytes:
    """Fetch raw bytes from the FDSN dataselect service for a station/window.

    Shared request plumbing for `fetch_geocsvseismogram`, `fetch_sac` and
    `fetch_mseed` — they differ only in the `format` value.
    """
    starttime = convert_to_utc_timestamp(starttime)
    endtime = convert_to_utc_timestamp(endtime)
    return http_get(
        _ServiceDefaults.dataselect_url,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "starttime": starttime.isoformat(),
            "endtime": endtime.isoformat(),
            "format": response_format,
        },
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    )


def fetch_geocsvseismogram(
    *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> bytes:
    """Fetch raw GeoCSV waveform bytes for a station/channel and time window.

    A lower-level counterpart to
    [`GeoCsvSeismogram.fetch`][pysmo.classes.GeoCsvSeismogram.fetch]:
    returns the waveform unparsed and uninterpreted. Save it to disk to
    defer parsing to later — offline, without another network request —
    via [`GeoCsvSeismogram.from_text`][pysmo.classes.GeoCsvSeismogram.from_text].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location, and
            channel for the request.
        starttime: Start of the requested time window (UTC).
        endtime: End of the requested time window (UTC).

    Returns:
        Raw GeoCSV document bytes.

    Raises:
        urllib3.exceptions.ResponseError: If the dataselect web service
            returns an HTTP error.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_geocsvseismogram
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> data = fetch_geocsvseismogram(
        ...     station=station,
        ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        ... )
        >>> _ = Path("ANMO.geocsv").write_bytes(data)
        >>>
        ```
        <!-- skip: end -->
    """
    return _fetch_dataselect(
        station=station,
        starttime=starttime,
        endtime=endtime,
        response_format="geocsv",
    )


def fetch_sac(
    *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> bytes:
    """Fetch a raw SAC zip archive for a station/channel and time window.

    A lower-level counterpart to [`SAC.fetch`][pysmo.classes.SAC.fetch]:
    returns the zip archive returned by the dataselect web service
    unparsed and uninterpreted, without extracting or reading any of its
    members. Save it to disk to defer parsing to later — offline, without
    another network request — via
    [`SAC.from_zip`][pysmo.classes.SAC.from_zip] or
    [`SAC.all_from_zip`][pysmo.classes.SAC.all_from_zip].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location, and
            channel for the request.
        starttime: Start of the requested time window (UTC).
        endtime: End of the requested time window (UTC).

    Returns:
        Raw zip archive bytes, as returned by the dataselect web service.

    Raises:
        urllib3.exceptions.ResponseError: If the dataselect web service
            returns an HTTP error.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_sac
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> data = fetch_sac(
        ...     station=station,
        ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        ... )
        >>> _ = Path("ANMO.sac.zip").write_bytes(data)
        >>>
        ```
        <!-- skip: end -->
    """
    return _fetch_dataselect(
        station=station,
        starttime=starttime,
        endtime=endtime,
        response_format="sac.zip",
    )


def fetch_mseed(
    *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> bytes:
    """Fetch raw miniSEED waveform bytes for a station/channel and time window.

    A lower-level counterpart to [`MSeed.fetch`][pysmo.classes.MSeed.fetch]:
    returns the miniSEED body returned by the dataselect web service
    unparsed and uninterpreted. Save it to disk to defer parsing to later —
    offline, without another network request — via
    [`MSeed.from_bytes`][pysmo.classes.MSeed.from_bytes] or
    [`MSeed.all_from_bytes`][pysmo.classes.MSeed.all_from_bytes].

    Args:
        station: Any object satisfying the [`Station`][pysmo.Station]
            protocol. Provides the network, station code, location, and
            channel for the request.
        starttime: Start of the requested time window (UTC).
        endtime: End of the requested time window (UTC).

    Returns:
        Raw miniSEED bytes, as returned by the dataselect web service. An
        empty `bytes` object if the service reports no data for the window.

    Raises:
        urllib3.exceptions.ResponseError: If the dataselect web service
            returns an HTTP error.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_mseed
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> data = fetch_mseed(
        ...     station=station,
        ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        ... )
        >>> _ = Path("ANMO.mseed").write_bytes(data)
        >>>
        ```
        <!-- skip: end -->
    """
    return _fetch_dataselect(
        station=station,
        starttime=starttime,
        endtime=endtime,
        response_format="miniseed",
    )


def _isoformat_or_none(value: pd.Timestamp | None) -> str | None:
    """Convert a timestamp to a UTC ISO 8601 string, passing `None` through."""
    return None if value is None else convert_to_utc_timestamp(value).isoformat()


def fetch_quakeml(
    *,
    starttime: pd.Timestamp | None = None,
    endtime: pd.Timestamp | None = None,
    updatedafter: pd.Timestamp | None = None,
    minlatitude: float | None = None,
    maxlatitude: float | None = None,
    minlongitude: float | None = None,
    maxlongitude: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    minradius: float | None = None,
    maxradius: float | None = None,
    mindepth_km: float | None = None,
    maxdepth_km: float | None = None,
    minmagnitude: float | None = None,
    maxmagnitude: float | None = None,
    magnitudetype: str | None = None,
    eventtype: str | None = None,
    eventid: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    orderby: QuakeMLOrderBy | None = None,
    catalog: str | None = None,
    contributor: str | None = None,
) -> bytes:
    """Fetch raw QuakeML 1.2 event metadata bytes from the USGS fdsnws-event service.

    A lower-level counterpart to
    [`QuakeML.all_from_query`][pysmo.classes.QuakeML.all_from_query]: returns
    the QuakeML document unparsed. All parameters are optional;
    `fetch_quakeml()` with no arguments is a valid "everything" request,
    bounded only by the service's own limits.

    Args:
        starttime: Keep events at or after this origin time (UTC).
        endtime: Keep events at or before this origin time (UTC).
        updatedafter: Keep events modified after this time (UTC).
        minlatitude: Southern edge of a bounding box, in degrees.
        maxlatitude: Northern edge of a bounding box, in degrees.
        minlongitude: Western edge of a bounding box, in degrees.
        maxlongitude: Eastern edge of a bounding box, in degrees.
        latitude: Centre latitude for a radial search, in degrees.
        longitude: Centre longitude for a radial search, in degrees.
        minradius: Inner radius for a radial search, in degrees.
        maxradius: Outer radius for a radial search, in degrees.
        mindepth_km: Minimum event depth, in **kilometres** (the
            fdsnws-event filter unit — the parsed
            [`QuakeML.depth`][pysmo.classes.QuakeML] is in metres).
        maxdepth_km: Maximum event depth, in **kilometres**.
        minmagnitude: Minimum event magnitude.
        maxmagnitude: Maximum event magnitude.
        magnitudetype: Magnitude type to filter on (e.g. `"Mw"`).
        eventtype: QuakeML event type, or a comma-separated list of them.
        eventid: Select a single event by the service's event id.
        limit: Maximum number of events to return.
        offset: Return events starting from this 1-based position.
        orderby: Sort order — one of `"time"`, `"time-asc"`, `"magnitude"`,
            `"magnitude-asc"`.
        catalog: Restrict to a named catalog.
        contributor: Restrict to a named contributor.

    Returns:
        Raw QuakeML 1.2 document bytes.

    Raises:
        urllib3.exceptions.ResponseError: If the event web service returns
            an HTTP error, including a 404 when no event matches.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo.tools.web import fetch_quakeml
        >>> xml = fetch_quakeml(
        ...     starttime=pd.Timestamp("2010-02-27T00:00:00Z"),
        ...     endtime=pd.Timestamp("2010-02-28T00:00:00Z"),
        ...     minmagnitude=8.0,
        ... )
        >>> _ = Path("maule.quakeml").write_bytes(xml)
        >>>
        ```
        <!-- skip: end -->
    """
    params: dict[str, Any] = {"format": "xml", "nodata": "404"}
    params["starttime"] = _isoformat_or_none(starttime)
    params["endtime"] = _isoformat_or_none(endtime)
    params["updatedafter"] = _isoformat_or_none(updatedafter)
    params.update(
        {
            "minlatitude": minlatitude,
            "maxlatitude": maxlatitude,
            "minlongitude": minlongitude,
            "maxlongitude": maxlongitude,
            "latitude": latitude,
            "longitude": longitude,
            "minradius": minradius,
            "maxradius": maxradius,
            "mindepth": mindepth_km,
            "maxdepth": maxdepth_km,
            "minmagnitude": minmagnitude,
            "maxmagnitude": maxmagnitude,
            "magnitudetype": magnitudetype,
            "eventtype": eventtype,
            "eventid": eventid,
            "limit": limit,
            "offset": offset,
            "orderby": orderby,
            "catalog": catalog,
            "contributor": contributor,
        }
    )
    return http_get(
        _ServiceDefaults.event_url,
        {name: value for name, value in params.items() if value is not None},
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    )


def fetch_station_inventory(
    *,
    network: str,
    station: str = "*",
    location: str = "*",
    channel: str,
    starttime: pd.Timestamp | None = None,
    endtime: pd.Timestamp | None = None,
    updatedafter: pd.Timestamp | None = None,
    minlatitude: float | None = None,
    maxlatitude: float | None = None,
    minlongitude: float | None = None,
    maxlongitude: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    minradius: float | None = None,
    maxradius: float | None = None,
    includerestricted: bool | None = None,
    matchtimeseries: bool | None = None,
) -> bytes:
    """Fetch raw FDSN StationXML inventory bytes from the EarthScope fdsnws-station service.

    A bulk, query-style counterpart to
    [`fetch_stationxml`][pysmo.tools.web.fetch_stationxml] (which is
    single-station and `level=response`). Returns a `level=channel`
    document covering every `<Channel>` epoch matching the query — parse it
    with [`StationXML.all_from_bytes`][pysmo.classes.StationXML.all_from_bytes]
    and narrow in memory (the results carry no `response`).

    `network` and `channel` are required (a query without them attempts to
    download the entire global inventory); `station` and `location` default
    to the FDSN "any" wildcard. Selection strings are sent verbatim, so the
    service's native comma-lists and `*` / `?` wildcards work
    (`network="IU,II"`, `channel="BH?"`).

    Args:
        network: Network code(s) — comma-list and `*` / `?` wildcards allowed.
        station: Station code(s), defaulting to all.
        location: Location code(s), defaulting to all.
        channel: Channel code(s) — comma-list and wildcards allowed.
        starttime: Keep metadata epochs intersecting at or after this time
            (UTC). Does not collapse to one epoch per channel.
        endtime: Keep metadata epochs intersecting at or before this time (UTC).
        updatedafter: Keep metadata modified after this time (UTC).
        minlatitude: Southern edge of a bounding box, in degrees.
        maxlatitude: Northern edge of a bounding box, in degrees.
        minlongitude: Western edge of a bounding box, in degrees.
        maxlongitude: Eastern edge of a bounding box, in degrees.
        latitude: Centre latitude for a radial search, in degrees.
        longitude: Centre longitude for a radial search, in degrees.
        minradius: Inner radius for a radial search, in degrees.
        maxradius: Outer radius for a radial search, in degrees.
        includerestricted: Include metadata for restricted stations
            (service default is `True`).
        matchtimeseries: Limit to metadata with recoverable timeseries data
            (service default is `False`; data-centre-dependent, can be slow).

    Returns:
        Raw StationXML document bytes.

    Raises:
        urllib3.exceptions.ResponseError: If the station web service returns
            an HTTP error, including a 404 when nothing matches.

    Examples:
        <!-- skip: start if(not run_real_web_requests) -->
        ```python
        >>> from pathlib import Path
        >>> from pysmo.tools.web import fetch_station_inventory
        >>> xml = fetch_station_inventory(network="IU", station="ANMO", channel="BHZ")
        >>> _ = Path("iu_anmo.xml").write_bytes(xml)
        >>>
        ```
        <!-- skip: end -->
    """
    params: dict[str, Any] = {
        "format": "xml",
        "nodata": "404",
        "level": "channel",
        "net": network,
        "sta": station,
        "loc": location,
        "cha": channel,
    }
    params["starttime"] = _isoformat_or_none(starttime)
    params["endtime"] = _isoformat_or_none(endtime)
    params["updatedafter"] = _isoformat_or_none(updatedafter)
    params.update(
        {
            "minlatitude": minlatitude,
            "maxlatitude": maxlatitude,
            "minlongitude": minlongitude,
            "maxlongitude": maxlongitude,
            "latitude": latitude,
            "longitude": longitude,
            "minradius": minradius,
            "maxradius": maxradius,
        }
    )
    for name, value in (
        ("includerestricted", includerestricted),
        ("matchtimeseries", matchtimeseries),
    ):
        if value is not None:
            params[name] = "true" if value else "false"
    return http_get(
        _ServiceDefaults.station_url,
        {name: value for name, value in params.items() if value is not None},
        timeout_seconds=_ServiceDefaults.timeout_seconds,
        request_retries=_ServiceDefaults.request_retries,
        retry_delay_seconds=_ServiceDefaults.retry_delay_seconds,
    )
