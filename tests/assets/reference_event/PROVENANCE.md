# Reference event: 2010-02-27 Maule, Chile

pysmo's primary test fixture identity, replacing the previously undocumented
`testfile.sac`. Chosen because it was already the de facto reference event in
three existing live-network tests (`tests/tools/test_web_live.py`,
`tests/integration/test_response_removal_live.py`,
`tests/lib/io/test_sacio.py`), rather than picking a new one.

- **Event**: 2010-02-27 Maule, Chile earthquake, M8.8. Origin lat `-36.122`,
  lon `-72.898`, depth `22900.0` m, origin time `2010-02-27T06:34:11.53Z`.
- **Station**: `IU.ANMO.00` (Albuquerque Seismological Laboratory), channels
  `BHZ` and `LHZ`. lat `34.945981`, lon `-106.457133`. Network `IU` is part
  of the Global Seismographic Network (USGS/EarthScope/NSF); its
  `restrictedStatus` is `open`.
- **Window**: `2010-02-27T06:44:06.04Z` to `2010-02-27T07:31:59.31Z`
  (~47.9 minutes, 57465 samples for BHZ at 20 Hz).
  - **Start**: predicted P arrival minus 2 minutes — predicted P via
    `haversine` (77.638° epicentral distance) + `fetch_travel_times`,
    P ≈ 714.513 s after origin, i.e. `2010-02-27T06:46:06.04Z`, matching
    `test_response_removal_live.py`'s convention. (Not to be confused with
    `test_web_live.py`'s `EXPECTED_TRAVEL_TIMES = {"P": 604.654, ...}` —
    that is a separate, hardcoded sanity-check geometry for
    `fetch_travel_times` itself, depth=22.9 km / distance=60°, unrelated to
    this event/station pair's actual 77.638° distance.)
  - **End**: origin time + (epicentral distance in km / 3.0 km/s) + 10
    minutes. An initial, phase-relative-only window (P − 2 min to P + 15
    min) was tried first and found inadequate: it ended before the S
    arrival had fully passed and long before surface waves — for a
    shallow (22.9 km) M8.8, often the largest-amplitude phase of the whole
    recording — which arrive tens of minutes after P, not tens of seconds.
    3.0 km/s is a conservative (slow) bound on the fundamental-mode
    Rayleigh/Love dispersion train's group velocity, chosen to cover the
    full dispersed wave train rather than just its fast onset; +10 minutes
    gives some coda after that. There is no single agreed rule for exactly
    how much margin is "enough" — this is a deliberate, documented choice,
    not a universal formula.

## Files

Every format EarthScope offers for this station/window, for both channels,
fetched as raw bytes/text — never parsed and re-serialised through pysmo's
own classes (see `fetch_reference_event.py`'s docstring for why):

- `iu_anmo_00_{bhz,lhz}.sac`
- `iu_anmo_00_{bhz,lhz}.mseed`
- `iu_anmo_00_{bhz,lhz}.geocsv`
- `iu_anmo_00_{bhz,lhz}_response.xml` (StationXML, `level=response`)
- `iu_anmo_00_{bhz,lhz}.pz` (SAC PZ)

`iu_anmo_00_bhz.sac` is the canonical fixture used throughout the test
suite (replacing `testfile.sac`). The LHZ set and non-SAC BHZ formats exist
for future-proofing (e.g. a future miniSEED reader) and multi-channel
StationXML coverage.

## Regenerating

```sh
python fetch_reference_event.py
. ./annotate_event_metadata.sh
```

`fetch_reference_event.py` downloads everything above from
`service.earthscope.org`. FDSN dataselect has no concept of an earthquake
event, so the two `.sac` files come back with no `evla`/`evlo`/`evdp`/`o`
header set. `annotate_event_metadata.sh` adds them afterwards using real
SAC's `ch` command (not pysmo's own writer — this keeps the annotation an
externally-produced edit rather than round-tripping through the exact code
these fixtures are meant to help validate), using the catalogue values
above. It only sets `evla`/`evlo`/`evdp`/`o`; the reference time
(`nzyear`/.../`b`) is left exactly as fetched (the true data start time),
so `o` is computed relative to that reference rather than moving it:
`o = -594.539` seconds (origin time minus the fetched reference time).

Note `iztype` is deliberately left as `unkn` (its default), not set to
`o`. Setting `iztype = "o"` is SAC's convention for declaring the
reference time *itself* to be the event origin — which is not what's
happening here (the reference time stays the true data start time; `o` is
just an ordinary offset from it). This has a real behavioural consequence
in pysmo: `SacEvent.time` can be freely reassigned on these files
(`sac.event.time = ...` works normally), unlike a file with `iztype ==
"o"`, where pysmo's `SacIO` locks `o` at `0` and raises `RuntimeError` on
any attempt to change it (see `tests/lib/io/test_sacio.py`'s
`test_iztype_prevents_zero_time_change`, which now constructs its own
minimal `SacIO()` for that specific case rather than relying on this
fixture, since this fixture no longer exercises it).

Requires a local SAC installation (`SACHOME`/`SACAUX`/`PATH` set per SAC's
own `sacinit.sh`) for the annotation step only.

## Licence / attribution

Network `IU` is part of the Global Seismographic Network, operated jointly
by the USGS, IRIS/EarthScope, and the NSF; its StationXML `restrictedStatus`
is `open` (verified for this station/epoch when the bundle was fetched —
re-check if regenerating far in the future, in case network policy
changes). Data served via `service.earthscope.org` (formerly IRIS DMC).
Event parameters (origin time/location/depth/magnitude) are public
earthquake-catalogue information for the 2010-02-27 Maule, Chile
earthquake, not derived from any single proprietary source.
