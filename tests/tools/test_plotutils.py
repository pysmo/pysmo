from datetime import UTC

import matplotlib  # type: ignore
import pandas as pd
import pytest
from matplotlib.figure import Figure

from pysmo import Seismogram

matplotlib.use("Agg")


@pytest.mark.mpl_image_compare(remove_text=True)
def test_plotutils_plotseis(
    seismograms: list[Seismogram],
) -> Figure:
    from pysmo.tools.plotutils import plotseis

    fig = plotseis(*seismograms, linewidth=0.5)  # type: ignore
    return fig


class TestPlotseisFunctions:
    def test_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from matplotlib.dates import num2date

        from pysmo.tools.plotutils import time_array

        times = time_array(seismogram)
        assert len(times) == len(seismogram.data)
        assert (
            pd.Timestamp(num2date(times[0])).timestamp()
            == seismogram.begin_time.timestamp()
        )
        assert (
            pd.Timestamp(num2date(times[-1])).timestamp()
            == seismogram.end_time.timestamp()
        )

    def test_unix_time_array(self, seismogram: Seismogram) -> None:
        """Get times from Seismogram object and verify them."""
        from pysmo.tools.plotutils import unix_time_array

        unix_times = unix_time_array(seismogram)
        assert len(unix_times) == len(seismogram.data)
        assert (
            pytest.approx(pd.Timestamp.fromtimestamp(unix_times[0], UTC).timestamp())
            == seismogram.begin_time.timestamp()
        )
        assert (
            pd.Timestamp.fromtimestamp(unix_times[-1], UTC).timestamp()
            == seismogram.end_time.timestamp()
        )

    def test_relative_time_array(self, seismogram: Seismogram) -> None:
        """Get relative times from Seismogram object and verify them."""
        from pysmo.tools.plotutils import relative_time_array

        # Reference before begin_time: all elapsed times are positive.
        reference = seismogram.begin_time - pd.Timedelta(seconds=10)
        rel_times = relative_time_array(seismogram, reference)
        assert len(rel_times) == len(seismogram.data)
        assert rel_times[0] == pytest.approx(
            (seismogram.begin_time - reference).total_seconds()
        )
        assert rel_times[-1] == pytest.approx(
            (seismogram.end_time - reference).total_seconds()
        )
        assert rel_times[0] > 0

        # Reference inside the trace: elapsed times change sign.
        reference = (
            seismogram.begin_time + (seismogram.end_time - seismogram.begin_time) / 2
        )
        rel_times = relative_time_array(seismogram, reference)
        assert rel_times[0] == pytest.approx(
            (seismogram.begin_time - reference).total_seconds()
        )
        assert rel_times[-1] == pytest.approx(
            (seismogram.end_time - reference).total_seconds()
        )
        assert rel_times[0] < 0 < rel_times[-1]
