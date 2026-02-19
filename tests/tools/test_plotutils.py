from pysmo import Seismogram
from pytest_cases import parametrize_with_cases
from pandas import Timestamp
from datetime import timezone
import pytest
import matplotlib  # type: ignore

matplotlib.use("Agg")


@pytest.mark.mpl_image_compare(remove_text=True)
def test_plotutils_plotseis(seismograms: tuple[Seismogram, ...]):  # type: ignore
    from pysmo.tools.plotutils import plotseis

    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig


@parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
class TestPlotseisFunctions:
    def test_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.tools.plotutils import time_array
        from matplotlib.dates import num2date

        times = time_array(seismogram)
        assert len(times) == len(seismogram)
        assert (
            Timestamp(num2date(times[0])).timestamp()
            == seismogram.begin_time.timestamp()
        )
        assert (
            Timestamp(num2date(times[-1])).timestamp()
            == seismogram.end_time.timestamp()
        )

    def test_unix_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.tools.plotutils import unix_time_array

        unix_times = unix_time_array(seismogram)
        assert len(unix_times) == len(seismogram)
        assert (
            pytest.approx(
                Timestamp.fromtimestamp(unix_times[0], timezone.utc).timestamp()
            )
            == seismogram.begin_time.timestamp()
        )
        assert (
            Timestamp.fromtimestamp(unix_times[-1], timezone.utc).timestamp()
            == seismogram.end_time.timestamp()
        )
