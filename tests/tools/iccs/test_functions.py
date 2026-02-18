from pysmo.tools.iccs import ICCS, update_all_picks
from pandas import Timedelta
from matplotlib.figure import Figure
import pytest


def test_update_pick(iccs_instance: ICCS) -> None:
    """Test updating a pick."""
    iccs = iccs_instance
    _ = iccs()
    org_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    pickdelta = Timedelta(seconds=1.23)
    update_all_picks(iccs, pickdelta)
    new_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    for org, new in zip(org_picks, new_picks):
        assert new - org == pickdelta


def test_update_pick_that_is_invalid(iccs_instance: ICCS) -> None:
    """Test if error is raised whith a bad pick."""

    from pysmo.tools.iccs._iccs import _calc_valid_pick_range

    iccs = iccs_instance
    min_t1, max_t1 = _calc_valid_pick_range(iccs)
    with pytest.raises(ValueError):
        update_all_picks(iccs, max_t1 + Timedelta(seconds=1))
    with pytest.raises(ValueError):
        update_all_picks(iccs, min_t1 - Timedelta(seconds=1))


class TestPlotCommonBase:
    PADDED = False
    ALL = False

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_initial(self, iccs_instance: ICCS) -> Figure:
        from pysmo.tools.iccs._functions import _plot_common_stack

        fig, _ = _plot_common_stack(
            iccs_instance, context=self.PADDED, show_all=self.ALL
        )
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_after(self, iccs_instance: ICCS) -> Figure:
        from pysmo.tools.iccs._functions import _plot_common_stack

        iccs_instance()

        fig, _ = _plot_common_stack(
            iccs_instance, context=self.PADDED, show_all=self.ALL
        )
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_initial(self, iccs_instance: ICCS) -> Figure:
        from pysmo.tools.iccs._functions import _plot_common_image

        fig, *_ = _plot_common_image(
            iccs_instance, context=self.PADDED, show_all=self.ALL
        )
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_after(self, iccs_instance: ICCS) -> Figure:
        from pysmo.tools.iccs._functions import _plot_common_image

        iccs_instance()

        fig, *_ = _plot_common_image(
            iccs_instance, context=self.PADDED, show_all=self.ALL
        )
        return fig


class TestPlotCommonAll(TestPlotCommonBase):
    ALL = True


class TestPlotCommonPadded(TestPlotCommonBase):
    PADDED = True


class TestPlotCommonAllPadded(TestPlotCommonBase):
    ALL = True
    PADDED = True
