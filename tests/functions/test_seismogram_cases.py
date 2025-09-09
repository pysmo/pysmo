from pysmo import MiniSeismogram
from pysmo.classes import SAC, SacSeismogram
from tests.conftest import TESTDATA

SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


def case_sac_seismogram() -> SacSeismogram:
    return SACSEIS


def case_mini_seismogram() -> MiniSeismogram:
    return MINISEIS
