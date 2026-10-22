# flake8: noqa: E402
"""On-demand fetching and preparation of waveforms for stations and events.

A [`PysmoProject`][pysmo.tools.project.PysmoProject] describes a pipeline that
fetches waveforms for a list of stations and prepares them for further
processing. The time window for each station is either derived from an event
or set explicitly. A project holds no waveform data itself, only its entries
and the functions that carry out each stage of the pipeline. There are three
stages, each with a default that can be replaced.

## Stage 1: Fetch window resolution

Projects are built from a list of
[`ProjectEntry`][pysmo.tools.project.ProjectEntry] objects. Each entry holds
a station, plus an event, an explicit window (`starttime`/`endtime`), or
both. The event is optional: an entry without one just needs an explicit
window. The first stage resolves each entry to an absolute fetch window, a [`WindowResult`][pysmo.tools.project.WindowResult]:

- An entry with an explicit window uses it as-is, even if it also has an
  event.
- Otherwise the project's `window` resolver derives the window from the
  entry's event. The default,
  [`PhaseWindow`][pysmo.tools.project.PhaseWindow], predicts the arrival of
  a seismic phase (P by default) at the station and returns the span
  `[arrival + pre_pick, arrival + post_pick]`.

```mermaid
flowchart LR
Entry(["`**ProjectEntry**`"])
Explicit{"`Explicit
window?`"}
Window["`**window**
default: **PhaseWindow**`"]
Result(["`**WindowResult**`"])
Entry --> Explicit
Explicit -->|Yes| Result
Explicit -->|No| Window --> Result
```

Tip: Custom window resolvers
    The `window` resolver holds the project's windowing policy: given an
    event and a station, it decides which stretch of time to fetch.
    `PhaseWindow` places it around a predicted phase arrival. A custom
    [`WindowResolver`][pysmo.tools.project.WindowResolver] can apply any
    other rule, such as a fixed span after the origin time, or a window
    around arrival times taken from an existing set of picks.

## Stage 2: Seismogram fetch

The second stage downloads the raw waveform for the entry's station over the
resolved window, using the project's `fetch_seismogram`. The default fetches
miniSEED from the EarthScope FDSN dataselect service via
[`MSeed.fetch`][pysmo.classes.MSeed.fetch], and goes to the network on every
fetch. A checksum of the first waveform fetched for an entry is recorded on
[`ProjectEntry.checksum`][pysmo.tools.project.ProjectEntry.checksum], so a
later fetch that returns different data is reported.

```mermaid
flowchart LR
Station(["`**ProjectEntry.station**`"])
Window(["`**WindowResult**`"])
Fetch["`**fetch_seismogram**
default: **MSeed.fetch**`"]
Raw(["`**Seismogram**`"])
Station --> Fetch
Window --> Fetch
Fetch --> Raw
```

Tip: Adding a cache
    Data in a live archive can change between fetches. Caching the miniSEED
    downloads on disk with a [`FetchCache`][pysmo.tools.cache.FetchCache]
    ensures every session of a project works with the same data (see
    "Caching downloads" below). A custom
    [`SeismogramFetcher`][pysmo.tools.project.SeismogramFetcher] is
    typically only needed for a different data centre or a local archive.

## Stage 3: Seismogram transformation

The third stage prepares the downloaded seismogram for downstream processing,
using the project's `seismogram_transform`, e.g. removing the instrument
response, detrending, and resampling. The transform also determines the
seismogram type the project returns. Alongside the seismogram, the
transform receives a [`FetchContext`][pysmo.tools.project.FetchContext]
with the entry, the window used for the fetch, and the `reference` from
stage 1, and it may make its own fetches, such as instrument response
metadata. The default copies the raw waveform into a
[`MiniSeismogram`][pysmo.MiniSeismogram] without any processing. The result
is kept in memory, so each entry is fetched and transformed only once for as
long as the project's settings stay unchanged.

```mermaid
flowchart LR
Raw(["`**Seismogram**`"])
Context(["`**FetchContext**`"])
Transform["`**seismogram_transform**
default: → **MiniSeismogram**`"]
Result(["`**TSeismogram**`"])
Raw --> Transform
Context --> Transform
Transform --> Result
```

Tip: Caching transformed data
    Wrapping the transform in a
    [`TransformCache`][pysmo.tools.project.TransformCache] stores its output
    on disk, so later sessions skip the processing and the transform's own
    fetches (see "Caching transformed seismograms" below). The waveform
    itself is still fetched by `fetch_seismogram`.

## Basic example

This example builds a project with a single entry, resolves its fetch
window, and fetches the seismogram, with no stage customised. The entry pairs IU.ANMO with the 2010-02-27 Maule, Chile M8.8
earthquake:

```python
>>> import pandas as pd
>>> from pysmo import MiniEvent, MiniStation
>>> from pysmo.tools.project import ProjectEntry, PysmoProject
>>>
>>> station_anmo = MiniStation(
...     name="ANMO", network="IU", location="00", channel="LHZ",
...     latitude=34.945981, longitude=-106.457133,
... )
>>> event_maule = MiniEvent(
...     latitude=-36.122, longitude=-72.898, depth=22900.0,
...     time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
... )
>>> entry = ProjectEntry(station=station_anmo, event=event_maule)
>>> project = PysmoProject(entries=[entry])
>>>
```

Discovery methods only inspect `entries` and fetch no data:

```python
>>> len(project.stations)
1
>>> project.events_for(station_anmo)
[MiniEvent(time=Timestamp('2010-02-27 06:34:11.530000+0000', tz='UTC'),
           latitude=-36.122, longitude=-72.898, depth=22900.0)]
>>>
```

The entry has an event and no explicit window, so stage 1 calls the default
`PhaseWindow`, which places the window around the predicted P arrival. This
fetches no data either.

```python
>>> window = project.window(entry)
>>> window.reference.floor("s")
Timestamp('2010-02-27 06:46:06+0000', tz='UTC')
>>> window.endtime - window.starttime
Timedelta('0 days 00:10:00')
>>>
```

Fetching the seismogram runs stages 2 and 3: the default
`fetch_seismogram` downloads miniSEED from EarthScope, and the default
`seismogram_transform` returns it unprocessed as a `MiniSeismogram`:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> seismogram = project.seismogram(station_anmo, event_maule)
>>> type(seismogram).__name__
'MiniSeismogram'
>>>
```
<!-- skip: end -->

## Building entries

A project may cover too many stations and events to write each
`ProjectEntry` by hand. [`build_entries`][pysmo.tools.project.build_entries]
creates the entries from lists of stations and events: it pairs every
station with every event and keeps the pairs an optional filter function
accepts. Its inputs are plain lists of stations and events. In the example
below, they are parsed from a station inventory and an event catalogue, then
narrowed with list comprehensions. The project is generic over the event and
station types it is built from, so `project.events` / `project.stations`
return those concrete types, not the bare [`Event`][pysmo.Event] /
[`Station`][pysmo.Station] protocols.

??? quote "example_catalogue.xml"
    ```xml
    --8<-- "docs/snippets/xml/example_catalogue.xml"
    ```

??? quote "example_inventory.xml"
    ```xml
    --8<-- "docs/snippets/xml/example_inventory.xml"
    ```

```python
>>> from pathlib import Path
>>> from pysmo import Event, Station
>>> from pysmo.classes import QuakeML, StationXML, resolve_epochs
>>> from pysmo.tools.azdist import haversine
>>> from pysmo.tools.project import build_entries
>>>
>>> events = QuakeML.all_from_bytes(Path("example_catalogue.xml").read_bytes())
>>> strong = [e for e in events if (e.magnitude or 0) >= 8.0]
>>> inventory = StationXML.all_from_bytes(Path("example_inventory.xml").read_bytes())
>>> bhz = [e for e in inventory if e.channel == "BHZ"]
>>> stations = resolve_epochs(bhz, strong[0].time)
>>> len(strong), len(stations)
(1, 1)
>>>
>>> def teleseismic_p(station: Station, event: Event) -> bool:
...     return haversine(event, station) <= 95.0
>>> entries = build_entries(stations, strong, teleseismic_p)
>>> project_from_catalogue = PysmoProject(entries=entries)
>>> [type(e).__name__ for e in project_from_catalogue.events]
['QuakeML']
>>> [type(s).__name__ for s in project_from_catalogue.stations]
['StationXML']
>>>
```

`entries` grows later without rebuilding, via a plain `extend`, since the
in-memory cache is keyed by entry content, not list position:

```python
>>> project_from_catalogue.entries.extend(
...     build_entries(stations, strong, teleseismic_p)
... )
>>> len(project_from_catalogue.entries)
2
>>>
```

## Customising the pipeline

### Fetch window

A window not tied to an event is set explicitly on the entry. The `window`
resolver is then not used:

```python
>>> fixed_window_project = PysmoProject(
...     entries=[
...         ProjectEntry(
...             station=station_anmo,
...             starttime="2010-02-27T05:00:00Z",
...             endtime="2010-02-27T06:00:00Z",
...         )
...     ],
... )
>>> fixed_window_project.events
[]
>>> fixed_window_project.events_for(station_anmo)
[None]
>>>
```

For windows derived from an event, the settings of `PhaseWindow` select the
phase, the span around its predicted arrival, and the travel-time model used
for the prediction. This example predicts arrivals with the ak135 model
instead of the default iasp91:

```python
>>> from functools import partial
>>> from pysmo.tools.project import PhaseWindow
>>> from pysmo.tools.traveltime import travel_times
>>>
>>> project_ak135 = PysmoProject(
...     entries=[entry],
...     window=PhaseWindow(travel_time_backend=partial(travel_times, model="ak135")),
... )
>>> arrivals = project_ak135.window.travel_time_backend(
...     depth=event_maule.depth, distance=60.0, phases=["P"]
... )
>>> round(arrivals["P"].total_seconds(), 1)
604.7
>>>
```

### Caching downloads

A [`FetchCache`][pysmo.tools.cache.FetchCache] as `fetch_seismogram` stores
each downloaded waveform on disk, so a station/window already fetched once
is read back locally on a later run, rather than re-fetched. Here it wraps
the same miniSEED download the default uses:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> from pysmo import Seismogram
>>> from pysmo.classes import MSeed
>>> from pysmo.tools.cache import FetchCache
>>> from pysmo.tools.web import fetch_mseed
>>>
>>> def parse_mseed(raw: bytes) -> Seismogram:
...     return MSeed.from_bytes(raw)
...
>>> waveform_cache = FetchCache(
...     path="waveform_cache.sqlite3", fetch_raw=fetch_mseed, parse=parse_mseed
... )
>>> download_cached_project = PysmoProject(
...     entries=[entry], fetch_seismogram=waveform_cache
... )
>>> one = download_cached_project.seismogram(station_anmo, event_maule)  # miss: fetched and stored
>>> download_cached_project.clear_cache()
>>> one_again = download_cached_project.seismogram(station_anmo, event_maule)  # hit: read from disk
>>>
```
<!-- skip: end -->

### Seismogram transform

This example prepares the data for [`ICCS`][pysmo.tools.iccs.ICCS], which
expects seismograms of type
[`MiniIccsSeismogram`][pysmo.tools.iccs.MiniIccsSeismogram] (or another
implementation of the `IccsSeismogram` type) with the instrument response
already removed. The `seismogram_transform` removes the response, then
converts the result into a `MiniIccsSeismogram`, using `context.reference`
(the predicted arrival) as the initial pick. It's a callable `attrs` class
rather than a plain function so `pre_filt` is configurable per instance:

```python
>>> from attrs import define
>>> from pysmo import Seismogram
>>> from pysmo.functions import clone_to_mini
>>> from pysmo.tools.iccs import ICCS, MiniIccsSeismogram
>>> from pysmo.tools.project import FetchContext
>>> from pysmo.tools.signal import remove_response
>>>
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
>>> iccs_project = PysmoProject(
...     entries=[entry],
...     seismogram_transform=to_mini_iccs_seismogram,
... )
>>>
```

Fetching a seismogram now downloads the waveform with the default
`fetch_seismogram`, and the instrument response with the transform's own
fetch; the result goes straight into `ICCS`:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> one = iccs_project.seismogram(station_anmo, event_maule)
>>> isinstance(one, MiniIccsSeismogram)
True
>>> iccs = ICCS(seismograms=iccs_project.seismograms_for(event_maule))
>>> len(iccs.seismograms)
1
>>>
```
<!-- skip: end -->

### Caching transformed seismograms

A [`TransformCache`][pysmo.tools.project.TransformCache] wrapping
`seismogram_transform` stores the transformed seismogram on disk. On a hit,
the transform is not run at all, so any processing and any fetches the
transform makes itself are skipped. The waveform is still fetched by
`fetch_seismogram`. Here it wraps a transform that detrends the data:

<!-- skip: start if(not run_real_web_requests) -->
```python
>>> from pysmo import MiniSeismogram, Seismogram
>>> from pysmo.functions import clone_to_mini, detrend
>>> from pysmo.tools.project import FetchContext, TransformCache
>>>
>>> def detrended(seismogram: Seismogram, context: FetchContext) -> MiniSeismogram:
...     mini = clone_to_mini(MiniSeismogram, seismogram)
...     detrend(mini)
...     return mini
...
>>> transform_cache = TransformCache(path="transform_cache.sqlite3", transform=detrended)
>>> transform_cached_project = PysmoProject(
...     entries=[entry], seismogram_transform=transform_cache
... )
>>> one = transform_cached_project.seismogram(station_anmo, event_maule)  # miss: transformed and stored
>>> transform_cached_project.clear_cache()
>>> one_again = transform_cached_project.seismogram(station_anmo, event_maule)  # hit: read from disk
>>> isinstance(one_again, MiniSeismogram)
True
>>>
```
<!-- skip: end -->

## Saving project state

The state of a project is saved with [`pickle`][]. It consists of the
entries (including their checksums), which `window`, `fetch_seismogram`,
and `seismogram_transform` are used along with their configuration, and an
optional `name` that labels the project. Neither waveform data nor the
in-memory cache are saved. Nor is the code behind the callables: loading a
saved project requires the same code to be importable.

`window`, `fetch_seismogram`, and `seismogram_transform` must each be a
top-level function in an importable module, a [`functools.partial`][] of
one, or an instance of a callable `attrs` class with only picklable fields;
not a lambda or closure. A callable that needs its own configuration (e.g.
filter corner frequencies) should be an `attrs` class. Its fields are saved with it, and they are what
`resolution_context_digest` uses to fingerprint `window` and
`seismogram_transform` (see "Identifying entries and changes" below). `PhaseWindow` is
one such class.

Unpickling runs arbitrary code, so a saved project is safe to load only when
it was produced locally or comes from a trusted source. The version check on
load detects a file written in an incompatible format; it is not a security
check, and runs after the file has already been unpickled. Sharing a project
with someone else therefore means sharing the Python code that builds it,
not the pickle file.

## Identifying entries and changes

Entries, project settings, and fetched waveforms each have an identifying
string. These allow a seismogram to be referred to outside the project, and
changes to the project or the archive data to be detected:

- [`entry.identity`][pysmo.tools.project.ProjectEntry.identity] identifies
  an entry by its station, event, and explicit window. It is computed
  without fetching anything. Passing it to
  [`project.get(identity)`][pysmo.tools.project.PysmoProject.get] fetches
  and transforms that entry, also on a project whose entries have never been
  fetched.
- [`project.resolution_context_digest`][pysmo.tools.project.PysmoProject.resolution_context_digest]
  identifies the settings that decide what a fetch returns: `window` and
  `seismogram_transform`. It changes when either of them does, before
  anything is fetched. Reassigning `fetch_seismogram` does not change it.
- [`entry.checksum`][pysmo.tools.project.ProjectEntry.checksum] identifies
  the waveform fetched for an entry, and only exists after the first fetch. A later fetch with a different checksum
  means the archive data have changed (see stage 2).

An entry built from the same station and event has the same identity, and
no checksum until it is fetched. Changing the `window` resolver changes the
digest:

```python
>>> from pysmo.tools.project import PhaseWindow
>>>
>>> same_entry = ProjectEntry(station=station_anmo, event=event_maule)
>>> same_entry.identity == entry.identity
True
>>> same_entry.identity[:3]
'v1:'
>>> same_entry.checksum is None
True
>>>
>>> identified_project = PysmoProject(entries=[same_entry])
>>> digest = identified_project.resolution_context_digest
>>> identified_project.window = PhaseWindow(phase="S")
>>> identified_project.resolution_context_digest == digest
False
>>>
```
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
