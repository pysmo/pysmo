"""
Run tests for all functions defined in pysmo.sac.sacfunc
"""

import os
import tempfile
import shutil
import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pysmo import SacIO, sacfunc


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
    assert pytest.approx(time[6]) == 53.18000
    assert pytest.approx(vals[6]) == -1591.0

def test_sac2xy_array(sacobj):
    """
    Get time and data as numpy arrays from SacFile
    object and verify their contents.
    """
    time, vals = sacfunc.sac2xy(sacobj, retarray=True)
    assert isinstance(time, np.ndarray)
    assert isinstance(vals, np.ndarray)
    assert pytest.approx(time[6]) == 53.18000
    assert pytest.approx(vals[6]) == -1591.0

@pytest.mark.mpl_image_compare(tolerance=20)
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
    assert pytest.approx(data_new[6]) == -1558.4662660

def test_detrend(sacobj):
    """Detrend SacFile object and verify mean is 0."""
    detrended_data = sacfunc.detrend(sacobj)
    assert np.mean(sacobj.data) != 0
    assert pytest.approx(np.mean(detrended_data)) == 0

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
    assert pytest.approx(azimuth_wgs84) == 177.78131677492817
    assert pytest.approx(azimuth_clrk66) == 177.7811794213202

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
    assert pytest.approx(azimuth_wgs84) == 357.03522613169105
    assert pytest.approx(azimuth_clrk66) == 357.0350879498619

def test_calcdist(sacobj):
    """
    Calculate distance from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function and
    verified against values obtained using the 'sac'
    binary itself.
    """
    azimuth_wgs84 = sacfunc.calc_dist(sacobj)
    azimuth_clrk66 = sacfunc.calc_dist(sacobj, ellps='clrk66')
    assert pytest.approx(azimuth_wgs84) == 3172.3886678422036
    assert pytest.approx(azimuth_clrk66) == 3172.276277170811

def test_envelope(sacobj):
    """
    Calculate gaussian envelope from SacFile object and verify
    the calculated values. The reference values were
    obtained from previous runs of this function.
    """
    Tn = 50 # Center Gaussian filter at 50s period
    alpha = 50 # Set alpha (which determines filterwidth) to 50
    envelope = sacfunc.envelope(sacobj, Tn, alpha)
    assert pytest.approx(envelope[6]) == 62.83288829293575

def test_gauss(sacobj):
    """
    Calculate gaussian filtered data from SacFile object and
    verify the calculated values. The reference values were
    obtained from previous runs of this function.
    """
    Tn = 50 # Center Gaussian filter at 50s period
    alpha = 50 # Set alpha (which determines filterwidth) to 50
    data = sacfunc.gauss(sacobj, Tn, alpha)
    assert pytest.approx(data[6]) == 26.17474984719684
