import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    draw_common_matrix_image,
    draw_common_stack,
)


class TestPlotCommonBase:
    PADDED = False
    ALL = False

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_initial(self, iccs_instance: ICCS) -> Figure:
        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_stack(
            ax, iccs_instance, context=self.PADDED, all_seismograms=self.ALL
        )
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_after(self, iccs_instance: ICCS) -> Figure:
        iccs_instance()

        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_stack(
            ax, iccs_instance, context=self.PADDED, all_seismograms=self.ALL
        )

        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_initial(self, iccs_instance: ICCS) -> Figure:
        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_matrix_image(
            ax, iccs_instance, context=self.PADDED, all_seismograms=self.ALL
        )

        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_after(self, iccs_instance: ICCS) -> Figure:
        iccs_instance()

        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_matrix_image(
            ax, iccs_instance, context=self.PADDED, all_seismograms=self.ALL
        )

        return fig


class TestPlotCommonAll(TestPlotCommonBase):
    ALL = True


class TestPlotCommonPadded(TestPlotCommonBase):
    PADDED = True


class TestPlotCommonAllPadded(TestPlotCommonBase):
    ALL = True
    PADDED = True
