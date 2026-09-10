# flake8: noqa: E402
"""Declare station/event data to fetch on demand, without storing it on disk.

A [`PysmoProject`][pysmo.tools.project.PysmoProject] holds a list of
[`ProjectEntry`][pysmo.tools.project.ProjectEntry] objects (a station, an
optional event, and an optional explicit window) plus a `seismogram_transform`
callable applied to each freshly downloaded [`Seismogram`][pysmo.Seismogram].
It defaults to returning the raw trace as a
[`MiniSeismogram`][pysmo.MiniSeismogram]; a custom transform is the place
for whatever data preparation a downstream tool needs (removing the
instrument response, detrending, resampling), as well as converting the
result into the target type that tool expects (e.g.
[`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram], for
[`ICCS`][pysmo.tools.iccs.ICCS]). Results are cached in memory for the life
of the object; nothing is ever written to disk by `PysmoProject` itself.

A `PysmoProject` is a small, reproducible definition rather than a data
store, so it is kept as a pickle rather than serialised to a bespoke config
format. Its three pluggable callables (`window`, `fetch_seismogram`,
`seismogram_transform`) must therefore be real top-level functions in an
importable module rather than lambdas or closures (pickle serialises
functions by reference, not by value). An optional `name` labels the project
for identification when persisted. A callable that needs its own
configuration (e.g. filter corner frequencies) should be a callable
[`attrs`][] class with only picklable fields (see the example below): it
pickles by value, and its declared fields are what let
`resolution_context_digest` fingerprint `window` and `seismogram_transform`.
A plain callable class pickles too, but the digest cannot read one.
[`PhaseWindow`][pysmo.tools.project.PhaseWindow], the default `window`, is
one such class.

Warning: A pickle is executable code
    Unpickling runs arbitrary code, so only ever load a project file you
    produced yourself or received from someone you trust. The version check
    on load guards against format drift, not against a hostile file; it runs
    after unpickling has already executed. To hand a project definition to
    someone else, share the Python that builds it, not the `.pkl`.

Build `entries` with
[`build_entries`][pysmo.tools.project.build_entries] from already-narrowed
lists of events and stations, a filtered cross product. The project is
generic over the event and station types it is built from, so
`project.events` / `project.stations` return those concrete types, not the
bare [`Event`][pysmo.Event] / [`Station`][pysmo.Station] protocols.

Pair `PysmoProject` with
[`FetchCache`][pysmo.tools.cache.FetchCache] as its `fetch_seismogram` so a
project's entries are only ever fetched once across however many sessions
the project is used in (see the second example below), provided `max_bytes`
is left at its unlimited default; a finite `max_bytes` evicts old entries,
which are then re-fetched on next access. A different mechanism from
[`ProjectEntry.checksum`][pysmo.tools.project.ProjectEntry.checksum], which
only detects drift on the live-network default rather than avoiding it.
Wrap `seismogram_transform` in a
[`TransformCache`][pysmo.tools.project.TransformCache] to cache the
transformed result, and whatever the transform fetches itself, on disk too.

## Basic example

This example builds a small project around a single, real station/event
pair: IU.ANMO recording the 2010-02-27 Maule, Chile M8.8 earthquake:

```python
>>> import pandas as pd
>>> from attrs import define
>>> from pysmo import Event, MiniEvent, MiniStation, Seismogram, Station
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

This `seismogram_transform` removes the instrument response, the data
preparation `ICCS` itself assumes has already happened (per its own
[`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply] docstring), then
converts the result into a `MiniIccsSeismogram`, using `context.reference`
(the predicted arrival) as the initial pick (see
[`FetchContext`][pysmo.tools.project.FetchContext]). It's a callable
`attrs` class rather than a plain function specifically so `pre_filt` is
configurable per instance:

```python
>>> @define(kw_only=True)
... class ToMiniIccsSeismogramWithResponseRemoved:
...     pre_filt: tuple[float, float, float, float]
...
...     def __call__(
...         self, seismogram: Seismogram, context: FetchContext[Station, Event]
...     ) -> MiniIccsSeismogram:
...         response = StationXML.fetch(
...             station=context.entry.station, time=context.starttime
...         ).response
...         corrected = clone_to_mini(
...             MiniIccsSeismogram, seismogram, update={"t0": context.reference}
...         )
...         remove_response(corrected, response, pre_filt=self.pre_filt)
...         return corrected
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

Discovery methods only inspect `entries`; no network access needed:

```python
>>> len(project.stations)
1
>>> project.events_for(station_anmo)
[MiniEvent(time=Timestamp('2010-02-27 06:34:11.530000+0000', tz='UTC'),
           latitude=-36.122, longitude=-72.898, depth=22900.0)]
>>>
```

Fetching a seismogram uses `PysmoProject`'s default `fetch_seismogram` for
the waveform, and `seismogram_transform`'s own fetch for the instrument
response; both download real data from EarthScope's FDSN web services:

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

## The fetch window

An entry's window comes from one of two places.

The first is the entry itself. If it sets `starttime` and `endtime`, that
window is used as-is and `window` is never called. A `ProjectEntry` with no
event is rejected unless it sets an explicit window, so every event-less
entry takes this path. An entry that carries an event can also set an
explicit window, to override the event-derived one.

```python
>>> pre_maule_noise = PysmoProject(
...     entries=[
...         ProjectEntry(
...             station=station_anmo,
...             starttime="2010-02-27T05:00:00Z",
...             endtime="2010-02-27T06:00:00Z",
...         )
...     ],
... )
>>> pre_maule_noise.events
[]
>>> pre_maule_noise.events_for(station_anmo)
[None]
>>>
```

The second is the `window` resolver. It runs when an entry has an event but
no explicit window. The default resolver is
[`PhaseWindow`][pysmo.tools.project.PhaseWindow]. It returns a span around
the predicted phase arrival. Its `phase`, `pre_pick`, `post_pick`, and
`travel_time_backend` fields live on the `PhaseWindow`, not on
`PysmoProject`. The example below sets `travel_time_backend` to the
built-in solver on the ak135 model:

```python
>>> from functools import partial
>>> from pysmo.tools.project import PhaseWindow
>>> from pysmo.tools.traveltime import travel_times
>>>
>>> project_ak135 = PysmoProject(
...     entries=[ProjectEntry(station=station_anmo, event=event_maule)],
...     window=PhaseWindow(travel_time_backend=partial(travel_times, model="ak135")),
... )
>>> arrivals = project_ak135.window.travel_time_backend(
...     depth=event_maule.depth, distance=60.0, phases=["P"]
... )
>>> round(arrivals["P"].total_seconds(), 1)
604.7
>>>
```

Any [`WindowResolver`][pysmo.tools.project.WindowResolver] can take the
place of `PhaseWindow`.

## Caching downloads

Pairing `fetch_seismogram` with
[`FetchCache`][pysmo.tools.cache.FetchCache] means a station/window already
fetched once is read back locally on a later run, rather than re-fetched;
recommended for real analysis work, over the always-fresh default used
above.

That only pins the waveform, though. `to_mini_iccs_seismogram` still
fetches a `StationXML` response itself on every call, and re-runs the
response removal, cached or not; a cache-backed `fetch_seismogram` says
nothing about whatever `seismogram_transform` independently does. Wrapping
the transform in a
[`TransformCache`][pysmo.tools.project.TransformCache] closes that gap: its
output is stored as JSON and reconstructed on a hit, transform and
secondary fetches skipped entirely.

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> from pysmo.classes import SAC
>>> from pysmo.tools.cache import FetchCache
>>> from pysmo.tools.project import TransformCache
>>> from pysmo.tools.web import fetch_sac
>>>
>>> def parse_sac_zip(raw: bytes) -> Seismogram:
...     return SAC.from_zip(raw).seismogram
...
>>> waveform_cache = FetchCache(
...     path="project_cache.sqlite3", fetch_raw=fetch_sac, parse=parse_sac_zip
... )
>>> transform_cache = TransformCache(
...     path="transform_cache.sqlite3", transform=to_mini_iccs_seismogram
... )
>>> cached_project = PysmoProject(
...     entries=[ProjectEntry(station=station_anmo, event=event_maule)],
...     seismogram_transform=transform_cache,
...     fetch_seismogram=waveform_cache,
... )
>>> one = cached_project.seismogram(station_anmo, event_maule)  # miss: fetches, transforms, stores
>>> one_again = cached_project.seismogram(station_anmo, event_maule)  # hit: nothing fetched or transformed
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

Grow it later without rebuilding, with a plain `extend`, since the fetch cache
is keyed by entry content, not list position:

```python
>>> project_as_code.entries.extend(build_entries(stations, strong, teleseismic_p))
>>> len(project_as_code.entries)
2
>>>
```

## Addressing entries

[`entry.identity`][pysmo.tools.project.ProjectEntry.identity] is a stable
string derived from the entry's natural key (normalised station code, event
hypocentre and origin time, or explicit window), computed without any fetch.
Persist it, and later pass it to
[`project.get(identity)`][pysmo.tools.project.PysmoProject.get] to fetch and
transform that one entry; `get` works on a project whose entries have never
been fetched.

[`project.resolution_context_digest`][pysmo.tools.project.PysmoProject.resolution_context_digest]
is a single digest over the parameters that decide what a fetch returns
(`window` and `seismogram_transform`). A consumer records it alongside the
identities and checks it once per session to detect that the project
definition has moved under it. Reassigning `fetch_seismogram` does not
change the digest.

The three are distinct:
- `entry.identity` is computable before any fetch, and is the persistable
  address.
- `project.resolution_context_digest` catches a definition change before a
  fetch is issued.
- `entry.checksum` catches a change in the fetched bytes, and only exists
  after a fetch.
"""

from ..._utils import export_module_names
from ._entry import ProjectEntry, build_entries
from ._identity import (
    UnknownEntryIdentity,
    callable_identity,
    entry_identity,
    entry_identity_components,
    resolution_context_digest,
)
from ._phasewindow import PhaseWindow
from ._project import PysmoProject
from ._transformcache import TransformCache
from ._types import (
    FetchContext,
    SeismogramFetcher,
    SeismogramTransform,
    WindowResolver,
    WindowResult,
)

__all__ = [
    "FetchContext",
    "PhaseWindow",
    "ProjectEntry",
    "PysmoProject",
    "SeismogramFetcher",
    "SeismogramTransform",
    "TransformCache",
    "UnknownEntryIdentity",
    "WindowResolver",
    "WindowResult",
    "build_entries",
    "callable_identity",
    "entry_identity",
    "entry_identity_components",
    "resolution_context_digest",
]

export_module_names(globals(), __name__)
