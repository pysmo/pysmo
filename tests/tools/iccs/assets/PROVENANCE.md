# ICCS test fixture provenance

22-station BHZ subset of [`data-example`](https://github.com/pysmo/data-example)'s
`fiji_region` event (2014-11-01 M7.1, Fiji region, 434 km deep — see that
repo's `PROVENANCE.md` for the full event/station-selection/window/
response-removal/annotation methodology).
Every file here already has its instrument response removed (`idep=vel`,
real ground velocity in m/s), an initial phase-arrival pick (`t0`, the
predicted P time), and is written as SAC v7 (`nvhdr=7`, double-precision
`o`/`t0`/etc.) — all done once, upstream, in `data-example`.

## Station selection

`derive_fixture.py` in this directory copies the 22 stations listed there
byte-for-byte from a local `data-example` checkout (no re-fetch, no
second round-trip through pysmo's writer).

| File | Network.Station | Latitude | Longitude | Distance (°) | Azimuth (°) |
|---|---|---|---|---|---|
| `ak_anm.bhz` | AK.ANM | 64.5646 | -165.3732 | 84.80 | 5.33 |
| `ak_barn.bhz` | AK.BARN | 61.0595 | -141.6622 | 85.80 | 16.69 |
| `ak_bpaw.bhz` | AK.BPAW | 64.0997 | -150.9873 | 86.33 | 11.43 |
| `ak_brse.bhz` | AK.BRSE | 59.7417 | -150.7414 | 82.44 | 13.42 |
| `ak_dhy.bhz` | AK.DHY | 63.0753 | -147.3759 | 86.14 | 13.33 |
| `ak_fid.bhz` | AK.FID | 60.7277 | -146.5987 | 84.26 | 14.80 |
| `ak_gamb.bhz` | AK.GAMB | 63.7758 | -171.7036 | 83.60 | 2.70 |
| `ak_goat.bhz` | AK.GOAT | 60.5805 | -144.7292 | 84.59 | 15.68 |
| `ak_grin.bhz` | AK.GRIN | 60.2805 | -143.3210 | 84.70 | 16.43 |
| `ak_kiag.bhz` | AK.KIAG | 60.9231 | -142.3605 | 85.50 | 16.48 |
| `ak_klu.bhz` | AK.KLU | 61.4924 | -145.9227 | 85.08 | 14.71 |
| `ak_kth.bhz` | AK.KTH | 63.5527 | -150.9233 | 85.84 | 11.69 |
| `ak_mcar.bhz` | AK.MCAR | 61.3836 | -143.0240 | 85.71 | 15.96 |
| `ak_mdm.bhz` | AK.MDM | 64.9602 | -148.2319 | 87.62 | 12.11 |
| `ak_mesa.bhz` | AK.MESA | 60.1785 | -141.9505 | 84.99 | 17.06 |
| `ak_pax.bhz` | AK.PAX | 62.9699 | -145.4699 | 86.47 | 14.14 |
| `ak_ppd.bhz` | AK.PPD | 65.5174 | -145.5246 | 88.66 | 12.83 |
| `ak_ptpk.bhz` | AK.PTPK | 61.1871 | -142.4672 | 85.69 | 16.29 |
| `ak_scm.bhz` | AK.SCM | 61.8320 | -147.3290 | 85.05 | 13.95 |
| `ak_wat6.bhz` | AK.WAT6 | 62.5808 | -147.7400 | 85.62 | 13.42 |
| `av_ive.bhz` | AV.IVE | 60.0163 | -153.0185 | 82.21 | 12.25 |
| `ta_a21k.bhz` | TA.A21K | 71.3221 | -156.6175 | 92.18 | 6.67 |

## Perturbation slots vs station geography

`tests/tools/iccs/conftest.py`'s `iccs_seismograms` fixture globs this
directory alphabetically and applies synthetic perturbations by index —
`[0]` gets a polarity flip, `[1]`/`[2]` get ±2s time shifts, `[3]` gets a
2x-decimation via `resample()`, `[4:]` (18 files) are left untouched. In
alphabetical order, that's currently `ak_anm` (flip), `ak_barn` (-2s),
`ak_bpaw` (+2s), `ak_brse` (resampled). This mapping is an arbitrary
test-harness convenience — it says nothing about those four stations'
geography or waveform quality, it's simply whichever files sort first.

The smaller, parallel Sybil-doctest fixture at `src/pysmo/conftest.py`
(only 3 of these same perturbations, no resample) globs the same directory
and inherits the same station set automatically.

## Regenerating

```sh
uv run python derive_fixture.py --data-example-path <path-to-data-example-checkout>
```

Defaults to a sibling `../../../../../data-example` checkout if
`--data-example-path` is omitted (this repo's usual on-disk layout).
