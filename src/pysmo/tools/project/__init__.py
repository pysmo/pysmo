# flake8: noqa: E402
"""Declare station/event data to fetch on demand, without storing it on disk.

A [`PysmoProject`][pysmo.tools.project.PysmoProject] holds a list of
[`ProjectEntry`][pysmo.tools.project.ProjectEntry] objects — station +
optional event + optional explicit window — plus a `seismogram_transform`
callable applied to each freshly downloaded
[`Seismogram`][pysmo.Seismogram]. It defaults to returning the raw trace as
a [`MiniSeismogram`][pysmo.MiniSeismogram]; a custom transform is the place
for whatever data preparation a downstream tool needs — removing the
instrument response, detrending, resampling — as well as converting the
result into the target type that tool expects (e.g.
[`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram], for
[`ICCS`][pysmo.tools.iccs.ICCS]). Results are cached in memory for the life
of the object; nothing is ever written to disk by `PysmoProject` itself. The
`PysmoProject` instance is the reproducible, shareable artefact — pickled,
not serialised to a bespoke config format, so `seismogram_transform` and
`fetch_seismogram` must be real top-level functions in an importable module
rather than lambdas or closures (pickle serialises functions by reference,
not by value). A callable `attrs` class with only picklable fields — see the
example below — is the alternative once the transform needs its own
configuration (e.g. filter corner frequencies): it pickles by value, so it
has no such restriction.

Build `entries` with
[`build_entries`][pysmo.tools.project.build_entries] from already-narrowed
lists of events and stations — a filtered cross product. The project is
generic over the event and station types it is built from, so
`project.events` / `project.stations` return those concrete types, not the
bare [`Event`][pysmo.Event] / [`Station`][pysmo.Station] protocols.

Pair `PysmoProject` with
[`SqliteArchiveFetcher`][pysmo.tools.archive.SqliteArchiveFetcher] as its
`fetch_seismogram` so a project's entries are only ever fetched once across
however many sessions the project is used in (see the second example
below) — a different mechanism from
[`ProjectEntry.checksum`][pysmo.tools.project.ProjectEntry.checksum], which
only detects drift on the live-network default rather than avoiding it.

## Basic example

This example builds a small project around a single, real station/event
pair — IU.ANMO recording the 2010-02-27 Maule, Chile M8.8 earthquake, the
same reference event used throughout this project's test suite and in
[`travel_times`][pysmo.tools.traveltime.travel_times]'s own `Examples:`
block:

```python
>>> import pandas as pd
>>> from attrs import define
>>> from pysmo import MiniEvent, MiniStation, Seismogram
>>> from pysmo.classes import StationXML
>>> from pysmo.functions import clone_to_mini
>>> from pysmo.tools.iccs import ICCS, MiniIccsSeismogram
>>> from pysmo.tools.project import FetchContext, ProjectEntry, PysmoProject
>>> from pysmo.tools.signal import remove_response
>>>
>>> station_anmo = MiniStation(
...     name="ANMO", network="IU", location="00", channel="LHZ",
...     latitude=34.945981, longitude=-106.457133,
... )
>>> event_maule = MiniEvent(
...     latitude=-36.122, longitude=-72.898, depth=22900.0,
...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
... )
>>>
```

This `seismogram_transform` removes the instrument response — data preparation
`ICCS` itself assumes has already happened, per its own
[`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] docstring — then
converts the result into a `MiniIccsSeismogram`, using the predicted
arrival on `context` as the initial pick (see
[`FetchContext`][pysmo.tools.project.FetchContext]). It's a callable
`attrs` class rather than a plain function specifically so `pre_filt` is
configurable per instance:

```python
>>> @define(kw_only=True)
... class ToMiniIccsSeismogramWithResponseRemoved:
...     pre_filt: tuple[float, float, float, float]
...
...     def __call__(
...         self, seismogram: Seismogram, context: FetchContext
...     ) -> MiniIccsSeismogram:
...         response = StationXML.fetch(
...             station=context.entry.station, time=context.starttime
...         ).response
...         corrected = remove_response(
...             seismogram, response, pre_filt=self.pre_filt, clone=True
...         )
...         return clone_to_mini(
...             MiniIccsSeismogram, corrected, update={"t0": context.predicted}
...         )
...
>>> to_mini_iccs_seismogram = ToMiniIccsSeismogramWithResponseRemoved(
...     # Teleseismic P on IU.ANMO's LHZ (1 Hz) channel: comfortably above
...     # the instrument's own corner and below the 0.5 Hz Nyquist.
...     pre_filt=(0.01, 0.02, 0.2, 0.3),
... )
>>> project = PysmoProject(
...     entries=[ProjectEntry(station=station_anmo, event=event_maule)],
...     seismogram_transform=to_mini_iccs_seismogram,
... )
>>>
```

Discovery methods only inspect `entries` — no network access needed:

```python
>>> len(project.stations)
1
>>> project.events_for(station_anmo)
[MiniEvent(time=Timestamp('2010-02-27 06:34:11.530000+0000', tz='UTC'), latitude=-36.122, longitude=-72.898, depth=22900.0)]
>>>
```

Fetching a seismogram uses `PysmoProject`'s default `fetch_seismogram` for
the waveform, and `seismogram_transform`'s own fetch for the instrument
response — both download real data from EarthScope's FDSN web services:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> one = project.seismogram(station_anmo, event_maule)
>>> isinstance(one, MiniIccsSeismogram)
True
>>> iccs = ICCS(seismograms=project.seismograms_for(event_maule))
>>> len(iccs.seismograms)
1
>>>
```
<!-- skip: end -->

## A different travel-time model

When an entry carries an event but no explicit window, the window is
placed around a predicted phase arrival — by default
[`travel_times`][pysmo.tools.traveltime.travel_times] on its own default
model. `travel_time_backend` swaps that for any callable of the same
shape ([`TravelTimeBackend`][pysmo.tools.traveltime.TravelTimeBackend]).
Here it is the same solver on the ak135 model, via
[`functools.partial`][]:

```python
>>> from functools import partial
>>> from pysmo.tools.traveltime import travel_times
>>>
>>> project_ak135 = PysmoProject(
...     entries=[ProjectEntry(station=station_anmo, event=event_maule)],
...     travel_time_backend=partial(travel_times, model="ak135"),
... )
>>> arrivals = project_ak135.travel_time_backend(
...     depth=event_maule.depth, distance=60.0, phases=["P"]
... )
>>> round(arrivals["P"].total_seconds(), 1)
604.7
>>>
```

The same hook takes a solver for a phase the built-in one does not
cover, or arrival times from an external catalogue.

## Caching downloads

Pairing `fetch_seismogram` with
[`SqliteArchiveFetcher`][pysmo.tools.archive.SqliteArchiveFetcher] means a
station/window already fetched once is read back locally on a later run,
rather than re-fetched — recommended for real analysis work, over the
always-fresh default used above.

This only pins the waveform, though. `to_mini_iccs_seismogram` (reused
below unchanged) still fetches a `StationXML` response itself on every call, cached
or not — an archive-backed `fetch_seismogram` says nothing about whatever
`seismogram_transform` independently fetches:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> from pysmo.classes import SAC
>>> from pysmo.tools.archive import SqliteArchiveFetcher
>>> from pysmo.tools.web import fetch_sac
>>>
>>> def parse_sac_zip(raw: bytes) -> Seismogram:
...     return SAC.from_zip(raw).seismogram
...
>>> archive = SqliteArchiveFetcher(
...     path="project_cache.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_zip
... )
>>> cached_project = PysmoProject(
...     entries=[ProjectEntry(station=station_anmo, event=event_maule)],
...     seismogram_transform=to_mini_iccs_seismogram,
...     fetch_seismogram=archive,
... )
>>> one = cached_project.seismogram(station_anmo, event_maule)  # waveform miss: fetches, stores
>>> one_again = cached_project.seismogram(station_anmo, event_maule)  # waveform hit; response still fetched
>>> isinstance(one_again, MiniIccsSeismogram)
True
>>>
```
<!-- skip: end -->

## Project as code

The recommended workflow: fetch broadly once (or load an inventory file),
parse each document to a flat list, narrow it with plain comprehensions you
can print and check, pair events with stations via
[`build_entries`][pysmo.tools.project.build_entries], then hand the result
to the one `PysmoProject` constructor. Everything after the initial fetch is
offline.

```python
>>> from pysmo import Event, Station
>>> from pysmo.classes import QuakeML, StationXML, resolve_epochs
>>> from pysmo.tools.azdist import haversine
>>> from pysmo.tools.project import build_entries
>>>
>>> catalogue = b'''<?xml version="1.0"?>
... <q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
...            xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
...   <eventParameters publicID="smi:example/catalogue">
...     <event publicID="smi:example/maule">
...       <origin publicID="smi:example/o1">
...         <time><value>2010-02-27T06:34:11.53Z</value></time>
...         <latitude><value>-36.122</value></latitude>
...         <longitude><value>-72.898</value></longitude>
...         <depth><value>22900</value></depth>
...       </origin>
...       <magnitude publicID="smi:example/m1"><mag><value>8.8</value></mag></magnitude>
...     </event>
...   </eventParameters>
... </q:quakeml>'''
>>> inventory = b'''<?xml version="1.0"?>
... <FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
...   <Network code="IU"><Station code="ANMO" startDate="1989-01-01T00:00:00">
...     <Latitude>34.945981</Latitude><Longitude>-106.457133</Longitude>
...     <Channel code="BHZ" locationCode="00" startDate="2008-06-30T20:00:00"
...              endDate="2011-02-18T19:11:00">
...       <Latitude>34.945981</Latitude><Longitude>-106.457133</Longitude>
...     </Channel>
...   </Station></Network>
... </FDSNStationXML>'''
>>>
>>> events = QuakeML.all_from_bytes(catalogue)
>>> strong = [e for e in events if (e.magnitude or 0) >= 8.0]
>>> bhz = [e for e in StationXML.all_from_bytes(inventory) if e.channel == "BHZ"]
>>> stations = resolve_epochs(bhz, strong[0].time)
>>> len(strong), len(stations)
(1, 1)
>>>
>>> def teleseismic_p(station: Station, event: Event) -> bool:
...     return haversine(event, station) <= 95.0
...
>>> entries = build_entries(stations, strong, teleseismic_p)
>>> project_as_code = PysmoProject(entries=entries)
>>> [type(e).__name__ for e in project_as_code.events]
['QuakeML']
>>> [type(s).__name__ for s in project_as_code.stations]
['StationXML']
>>>
```

Grow it later without rebuilding — a plain `extend`, since the fetch cache
is keyed by entry content, not list position:

```python
>>> project_as_code.entries.extend(build_entries(stations, strong, teleseismic_p))
>>> len(project_as_code.entries)
2
>>>
```
"""

from ..._utils import export_module_names
from ._entry import ProjectEntry, build_entries
from ._project import FetchContext, PysmoProject

__all__ = ["FetchContext", "ProjectEntry", "PysmoProject", "build_entries"]

export_module_names(globals(), __name__)
