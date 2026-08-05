#! /bin/sh
# FDSN dataselect never carries earthquake-event metadata (it only knows
# about the station/channel), so evla/evlo/evdp/o are absent on the SAC
# files fetch_reference_event.py downloads. Add them here via real SAC's
# `ch` command (not pysmo's own writer, keeping this an externally-produced
# annotation) using the well-documented 2010-02-27 Maule, Chile catalogue
# values already used verbatim elsewhere in this test suite (see
# PROVENANCE.md). Only evla/evlo/evdp/o are set; nzyear/nzjday/.../b are
# left exactly as fetched (the real data start time), so `o` is computed
# relative to that reference rather than moving the reference itself.
#
# Run once after fetch_reference_event.py, from this directory:
#   . ./annotate_event_metadata.sh

sac <<EOF
r iu_anmo_00_bhz.sac
ch evla -36.122 evlo -72.898 evdp 22.9 o -594.539
wh
r iu_anmo_00_lhz.sac
ch evla -36.122 evlo -72.898 evdp 22.9 o -594.539
wh
q
EOF
