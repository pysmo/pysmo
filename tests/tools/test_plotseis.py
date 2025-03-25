from pysmo import Seismogram, MiniSeismogram
from pysmo.classes import SAC
import pytest
import pytest_cases
import matplotlib  # type: ignore
from tests.conftest import TESTDATA

matplotlib.use("Agg")


SACSEIS = SAC.from_file(TESTDATA["orgfile"]).seismogram
MINISEIS = MiniSeismogram(
    begin_time=SACSEIS.begin_time,
    delta=SACSEIS.delta,
    data=SACSEIS.data,
)


@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir="../baseline/")
def test_plotseis(seismograms: tuple[Seismogram, ...]):  # type: ignore
    from pysmo.tools.plotseis import plotseis

    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


@pytest_cases.parametrize(
    "seismogram", (SACSEIS, MINISEIS), ids=("SacSeismogram", "MiniSeismogram")
)
class test_plotseisFunctions:
    def test_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.tools.plotseis import time_array
        from matplotlib.dates import num2date

        times = time_array(seismogram)
        assert len(times) == len(seismogram)
        assert num2date(times[0]) == seismogram.begin_time
        assert num2date(times[-1]) == seismogram.end_time

    def test_unix_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.tools.plotseis import unix_time_array
        from datetime import datetime, timezone

        unix_times = unix_time_array(seismogram)
        assert len(unix_times) == len(seismogram)
        assert (
            datetime.fromtimestamp(unix_times[0], timezone.utc) == seismogram.begin_time
        )
        assert (
            datetime.fromtimestamp(unix_times[-1], timezone.utc) == seismogram.end_time
        )
