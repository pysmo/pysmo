from pysmo import Seismogram
from pysmo.functions import plotseis
import matplotlib.pyplot as plt  # type: ignore
import pytest
import matplotlib
matplotlib.use('Agg')


@pytest.mark.mpl_image_compare(remove_text=True, baseline_dir='../baseline/')
def test_plotseis(seismograms: tuple[Seismogram, ...]) -> plt.figure:
    fig = plotseis(*seismograms, showfig=False, linewidth=0.5)  # type: ignore
    return fig
