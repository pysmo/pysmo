"""
Run tests for all functions defined in pysmo.sac.sacfunc
"""

import matplotlib.pyplot as plt
from pysmo import SacIO, sacfunc
import os
import tempfile
import shutil
import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')


@pytest.fixture()
def tmpdir():
    """
    Create a temporary directory for tests and
    remove it when done.
    """
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)


@pytest.fixture()
def testfile():
    """Determine absolute path of the test SAC file."""
    return os.path.join(os.path.dirname(__file__), 'testfile.sac')


@pytest.fixture()
def sacobj(tmpdir, testfile):
    """Return read-only SacFile object"""
    tmpfile = os.path.join(tmpdir, 'tmpfile.sac')
    shutil.copyfile(testfile, tmpfile)
    return SacIO.from_file(tmpfile)


def test_sac2xy_list(sacobj):
    """
    Get time and data as lists from SacFile object
    and verify their contents.
    """
    time, vals = sacfunc.sac2xy(sacobj)
    assert isinstance(time, list)
    assert isinstance(vals, list)
    assert pytest.approx(time[6]) == -63.2200001552701
    assert pytest.approx(vals[6]) == 2378.0


def test_sac2xy_array(sacobj):
    """
    Get time and data as numpy arrays from SacFile
    object and verify their contents.
    """
    time, vals = sacfunc.sac2xy(sacobj, retarray=True)
    assert isinstance(time, np.ndarray)
    assert isinstance(vals, np.ndarray)
    assert pytest.approx(time[6]) == -63.2200001552701
    assert pytest.approx(vals[6]) == 2378.0


@pytest.mark.mpl_image_compare(remove_text=True)
def test_plotsac(sacobj):
    """
    Plot SAC object and compare it to
    reference image.
    """
    fig = plt.figure()
    sacfunc.plotsac(sacobj, showfig=False)
    return fig


def test_resample(sacobj):
    """Resample SacFile object and verify resampled data."""
    delta_old = sacobj.delta
    delta_new = delta_old * 2
    data_new = sacfunc.resample(sacobj, delta_new)
    assert pytest.approx(data_new[6]) == 2202.0287804516634


def test_detrend(sacobj):
    """Detrend SacFile object and verify mean is 0."""
    detrended_data = sacfunc.detrend(sacobj)
    assert np.mean(sacobj.data) != 0
    assert pytest.approx(np.mean(detrended_data), abs=1e-6) == 0


def test_calcaz(sacobj):
    """
    Calculate azimuth from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function and
    verified against values obtained using the 'sac'
    binary itself.
    """
    azimuth_wgs84 = sacfunc.calc_az(sacobj)
    azimuth_clrk66 = sacfunc.calc_az(sacobj, ellps='clrk66')
    assert pytest.approx(azimuth_wgs84) == 181.9199258637492
    assert pytest.approx(azimuth_clrk66) == 181.92001941872516


def test_calcbaz(sacobj):
    """
    Calculate back azimuth from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function and
    verified against values obtained using the 'sac'
    binary itself.
    """
    azimuth_wgs84 = sacfunc.calc_baz(sacobj)
    azimuth_clrk66 = sacfunc.calc_baz(sacobj, ellps='clrk66')
    assert pytest.approx(azimuth_wgs84) == 2.4677533885335947
    assert pytest.approx(azimuth_clrk66) == 2.467847115319614


def test_calcdist(sacobj):
    """
    Calculate distance from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function and
    verified against values obtained using the 'sac'
    binary itself.
    """
    dist_wgs84 = sacfunc.calc_dist(sacobj)
    dist_clrk66 = sacfunc.calc_dist(sacobj, ellps='clrk66')
    assert pytest.approx(dist_wgs84) == 1889.1549940066523
    assert pytest.approx(dist_clrk66) == 1889.1217781364019


def test_envelope(sacobj):
    """
    Calculate gaussian envelope from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    envelope = sacfunc.envelope(sacobj, Tn, alpha)
    assert pytest.approx(envelope[100]) == 6.109130497913114


def test_gauss(sacobj):
    """
    Calculate gaussian filtered data from SacFile object and
    verify the calculated values. The reference values were
    obtained from previous runs of this function.
    """
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    data = sacfunc.gauss(sacobj, Tn, alpha)
    assert pytest.approx(data[100]) == -5.639860165811819


@pytest.mark.depends(on=['test_envelope', 'test_gauss'])
@pytest.mark.mpl_image_compare(remove_text=True)
def test_plot_gauss_env(sacobj):
    Tn = 50  # Center Gaussian filter at 50s period
    alpha = 50  # Set alpha (which determines filterwidth) to 50
    time, vals = sacfunc.sac2xy(sacobj, retarray=False)
    vals = vals - np.mean(vals)
    fig = plt.figure()
    plt.plot(time, vals, linewidth=0.01, color='black')
    plt.plot(time, sacfunc.envelope(sacobj, Tn, alpha), color='blue')
    plt.plot(time, sacfunc.gauss(sacobj, Tn, alpha), color='red')
    plt.xlabel('Time[s]')
    plt.xlim([100, 1200])
    return(fig)
