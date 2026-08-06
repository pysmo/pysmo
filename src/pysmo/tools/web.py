"""Tools for fetching seismological data from web services."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Self

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
    "TravelTimeBackend",
    "fetch_geocsvseismogram",
    "fetch_sac",
    "fetch_sacpz",
    "fetch_stationxml",
    "fetch_travel_times",
]

type TravelTimeBackend = Callable[[float, float, list[str]], dict[str, float]]
"""Callable `(depth_km, dist_deg, phases) -> dict[str, float]` returning travel times.

Accepts source depth in kilometres, epicentral distance in degrees, and a list of
seismic phase names (e.g. `["P", "S"]`). Returns a mapping of phase name to
travel time in seconds, omitting phases with no arrival at the given geometry.
"""


@dataclass(init=False)
class _EarthScopeDefaults:
    def __new__(cls) -> Self:
        raise RuntimeError(
            "_EarthScopeDefaults is not meant to be instantiated. "
            "Use _EarthScopeDefaults.<attribute> instead."
        )

    traveltime_url: str = "https://service.earthscope.org/irisws/traveltime/1/query"
    station_url: str = "https://service.earthscope.org/fdsnws/station/1/query"
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
        >>> seismogram = GeoCsvSeismogram.fetch(  # doctest: +SKIP
        ...     station=station,
        ...     starttime=predicted_p - pd.Timedelta(minutes=2),
        ...     endtime=predicted_p + pd.Timedelta(minutes=8),
        ... )
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
        ```python
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_stationxml
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="BHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> xml = fetch_stationxml(station=station)  # doctest: +SKIP
        >>> Path("ANMO.xml").write_bytes(xml)  # doctest: +SKIP
        >>>
        ```
    """
    return http_get(
        _EarthScopeDefaults.station_url,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "level": "response",
        },
        timeout_seconds=_EarthScopeDefaults.timeout_seconds,
        request_retries=_EarthScopeDefaults.request_retries,
        retry_delay_seconds=_EarthScopeDefaults.retry_delay_seconds,
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
            service defaults to the currently-open epoch.

    Returns:
        Raw SAC PZ text.

    Raises:
        urllib3.exceptions.ResponseError: If the web service returns an HTTP
            error.

    Examples:
        ```python
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_sacpz
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="BHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> text = fetch_sacpz(station=station)  # doctest: +SKIP
        >>> Path("ANMO.pz").write_text(text)  # doctest: +SKIP
        >>>
        ```
    """
    params = {
        "net": station.network,
        "sta": station.name,
        "loc": station.location,
        "cha": station.channel,
    }
    if time is not None:
        params["time"] = convert_to_utc_timestamp(time).isoformat()
    return http_get(
        _EarthScopeDefaults.sacpz_url,
        params,
        timeout_seconds=_EarthScopeDefaults.timeout_seconds,
        request_retries=_EarthScopeDefaults.request_retries,
        retry_delay_seconds=_EarthScopeDefaults.retry_delay_seconds,
    ).decode("ascii")


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
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_geocsvseismogram
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> data = fetch_geocsvseismogram(  # doctest: +SKIP
        ...     station=station,
        ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        ... )
        >>> Path("ANMO.geocsv").write_bytes(data)  # doctest: +SKIP
        >>>
        ```
    """
    starttime = convert_to_utc_timestamp(starttime)
    endtime = convert_to_utc_timestamp(endtime)
    return http_get(
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


def fetch_sac(
    *, station: Station, starttime: pd.Timestamp, endtime: pd.Timestamp
) -> bytes:
    """Fetch a raw SAC zip archive for a station/channel and time window.

    A lower-level counterpart to [`SAC.fetch`][pysmo.classes.SAC.fetch]:
    returns the zip archive returned by the dataselect web service
    unparsed and uninterpreted, without extracting or reading any of its
    members. Save it to disk to defer parsing to later — offline,
    without another network request.

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
        ```python
        >>> import pandas as pd
        >>> from pathlib import Path
        >>> from pysmo import MiniStation
        >>> from pysmo.tools.web import fetch_sac
        >>> station = MiniStation(
        ...     name="ANMO", network="IU", location="00", channel="LHZ",
        ...     latitude=34.945981, longitude=-106.457133,
        ... )
        >>> data = fetch_sac(  # doctest: +SKIP
        ...     station=station,
        ...     starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
        ...     endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        ... )
        >>> Path("ANMO.sac.zip").write_bytes(data)  # doctest: +SKIP
        >>>
        ```
    """
    starttime = convert_to_utc_timestamp(starttime)
    endtime = convert_to_utc_timestamp(endtime)
    return http_get(
        _EarthScopeDefaults.dataselect_url,
        {
            "net": station.network,
            "sta": station.name,
            "loc": station.location,
            "cha": station.channel,
            "starttime": starttime.isoformat(),
            "endtime": endtime.isoformat(),
            "format": "sac.zip",
        },
        timeout_seconds=_EarthScopeDefaults.timeout_seconds,
        request_retries=_EarthScopeDefaults.request_retries,
        retry_delay_seconds=_EarthScopeDefaults.retry_delay_seconds,
    )
