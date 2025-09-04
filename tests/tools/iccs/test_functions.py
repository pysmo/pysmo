from __future__ import annotations
from pysmo.tools.iccs import ICCS, update_pick
from datetime import timedelta


def test_update_pick(iccs_instance: ICCS) -> None:
    """Test updating a pick."""
    iccs = iccs_instance
    _ = iccs()
    org_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    pickdelta = timedelta(seconds=1.23)
    update_pick(iccs, pickdelta)
    new_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    for org, new in zip(org_picks, new_picks):
        assert new - org == pickdelta
