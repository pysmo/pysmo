"""
Run tests for the SacIO class
"""

import os
import tempfile
import shutil
import pytest
import copy
import pickle
from pysmo import SacIO


# Note: this fixture is only needed for python2
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
def tmpfiles(tmpdir):
    """
    Define 3 tempfiles for testing.
    - tmpfile1: copy of reference file, which is not modified during test
    - tmpfile2: copy of reference file, which is modified during test
    - tmpfile3: used to write a new sac file
    - tmpfile4: used to test pickling
    """
    orgfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    tmpfile1 = os.path.join(tmpdir, 'tmpfile1.sac')
    tmpfile2 = os.path.join(tmpdir, 'tmpfile2.sac')
    tmpfile3 = os.path.join(tmpdir, 'tmpfile2.sac')
    tmpfile4 = os.path.join(tmpdir, 'tmpfile4.pickle')
    shutil.copyfile(orgfile, tmpfile1)
    shutil.copyfile(orgfile, tmpfile2)
    return tmpfile1, tmpfile2, tmpfile3, tmpfile4

@pytest.fixture()
def instances(tmpfiles):
    """Copy reference sac file to tmpdir"""
    tmpfile1, tmpfile2, _, _ = tmpfiles
    return SacIO.from_file(tmpfile1), SacIO.from_file(tmpfile2)

@pytest.mark.dependancy()
def test_is_sacio_type(instances):
    sac1, sac2 = instances
    assert isinstance(sac1, SacIO)
    assert isinstance(sac2, SacIO)

@pytest.mark.dependancy(depends=['test_is_sacio_type'])
def test_read_headers(instances):
    """
    Read all SAC headers from a test file
    """
    sac, _ = instances
    assert sac.npts == 180000
    assert sac.b == pytest.approx(53.060001373291016)
    assert sac.e == pytest.approx(3653.0400390625)
    assert sac.iftype == 'time'
    assert sac.leven == True
    assert sac.delta == pytest.approx(0.02)
    assert sac.odelta is None
    assert sac.idep == 'unkn'
    assert sac.depmin == pytest.approx(-8293.0)
    assert sac.depmax == pytest.approx(3302.0)
    assert sac.depmen == pytest.approx(-572.200439453125)
    assert sac.o == pytest.approx(0.0)
    assert sac.a is None
    assert sac.t0 is None
    assert sac.t1 is None
    assert sac.t2 is None
    assert sac.t3 is None
    assert sac.t4 is None
    assert sac.t5 is None
    assert sac.t6 is None
    assert sac.t7 is None
    assert sac.t8 is None
    assert sac.t9 is None
    assert sac.f is None
    # kzdate is a derived header
    # kztime is a derived header
    assert sac.iztype == 'o'
    assert sac.kinst is None
    assert sac.resp0 is None
    assert sac.resp1 is None
    assert sac.resp2 is None
    assert sac.resp3 is None
    assert sac.resp4 is None
    assert sac.resp5 is None
    assert sac.resp6 is None
    assert sac.resp7 is None
    assert sac.resp8 is None
    assert sac.resp9 is None
    assert sac.kdatrd is None
    assert sac.kstnm == 'MEL01'
    assert sac.cmpaz == pytest.approx(0)
    assert sac.cmpinc == pytest.approx(90)
    assert sac.istreg is None
    assert sac.stla == pytest.approx(-43.855464935302734)
    assert sac.stlo == pytest.approx(-73.74272155761719)
    assert sac.stel is None
    assert sac.stdp is None
    assert sac.kevnm == '043550359BHN'
    assert sac.ievreg is None
    assert sac.evla == pytest.approx(-15.265999794006348)
    assert sac.evlo == pytest.approx(-75.20800018310547)
    assert sac.evel is None
    assert sac.evdp == pytest.approx(30.899999618530273)
    assert sac.ievtyp == 'quake'
    assert sac.khole == ''
    assert sac.dist == pytest.approx(3172.399658203125)
    assert sac.az == pytest.approx(177.77978515625)
    assert sac.baz == pytest.approx(357.0372619628906)
    assert sac.gcarc == pytest.approx(28.522098541259766)
    assert sac.lovrok == True
    assert sac.iqual is None
    assert sac.isynth is None
    assert sac.user0 is None
    assert sac.user1 is None
    assert sac.user2 is None
    assert sac.user3 is None
    assert sac.user4 is None
    assert sac.user5 is None
    assert sac.user6 is None
    assert sac.user7 is None
    assert sac.user8 == pytest.approx(4.900000095367432)
    assert sac.user9 == pytest.approx(5.000000)
    assert sac.kuser0 is None
    assert sac.kuser1 is None
    assert sac.kuser2 is None
    assert sac.nxsize is None
    assert sac.xminimum is None
    assert sac.xmaximum is None
    assert sac.nysize is None
    assert sac.yminimum is None
    assert sac.ymaximum is None
    assert sac.nvhdr == 6
    assert sac.scale is None
    assert sac.norid == 0
    assert sac.nevid == 0
    assert sac.nwfid == 13
    assert sac.iinst is None
    assert sac.lpspol == True
    assert sac.lcalda == True
    assert sac.kcmpnm == 'BHN'
    assert sac.knetwk == 'YJ'
    assert sac.mag is None
    assert sac.imagtyp is None
    assert sac.imagsrc is None
    # try reading non-existing header
    with pytest.raises(AttributeError): sac.nonexistingheader

@pytest.mark.dependancy(depends=['test_is_sacio_type'])
def test_read_data(instances):
    sac, _ = instances
    assert sac.data[:10] == [-1616.0, -1609.0, -1568.0, -1606.0, -1615.0, -1565.0, -1591.0, -1604.0, -1601.0, -1611.0]

@pytest.mark.dependancy(depends=['test_read_headers'])
def test_change_headers(instances):
    """
    Test changing header values
    """
    
    sac1, sac2 = instances

    iftype_valid = 'time'
    iftype_invalid = 'asdfasdf'
    
    # set iftype to a valid value
    sac2.iftype = iftype_valid
    assert sac2.iftype == iftype_valid

    # set iftype to an invalid value
    with pytest.raises(ValueError): sac2.iftype = iftype_invalid

    # Try setting a header that should only accept strings to a boolean
    with pytest.raises(ValueError): sac2.kuser0 = True

    # Try setting a string that is too long
    with pytest.raises(ValueError): sac2.kuser0 = 'too long string'

    # Are trailing spaces removed?
    sac2.kuser0 = 'aaaa   '
    assert sac2.kuser0 == 'aaaa'

    # Does changing header fields in one instance effect another?
    delta_old = sac2.delta
    sac2.delta = 2 * delta_old
    assert sac1.delta == pytest.approx(delta_old)
    assert sac2.delta == pytest.approx(2 * delta_old)

    # has the end time changed by changing delta?
    assert sac1.e != sac2.e

@pytest.mark.dependancy(depends=['test_read_headers', 'test_read_data'])
def test_change_data(instances):
    """
    Test changing data
    """
    _, sac2 = instances
    newdata = [132, 232, 3465, 111]
    olddata = sac2.data
    sac2.data = newdata
    assert sac2.data == newdata
    assert sac2.depmin == min(newdata)
    assert sac2.depmax == max(newdata)
    assert sac2.depmen == sum(newdata)/sac2.npts

@pytest.mark.dependancy(depends=['test_change_headers', 'test_change_data'])
def test_write_to_file(instances, tmpfiles):
    sac1, _ = instances
    _, _, tmpfile3, _ = tmpfiles
    sac1.write(tmpfile3)
    sac3 = SacIO.from_file(tmpfile3)
    assert sac1.data == sac3.data
    assert sac1.b == sac3.b

@pytest.mark.dependancy(depends=['test_read_headers', 'test_read_data'])
def test_pickling(instances, tmpfiles):
    sac1, _ = instances
    _, _, _, tmpfile4 = tmpfiles
    with open(tmpfile4, "wb") as output_file:
        pickle.dump(sac1, output_file)
    with open(tmpfile4, "rb") as input_file:
        sac4 = pickle.load(input_file)
    assert sac1.data == sac4.data
    assert sac1.b == sac4.b

@pytest.mark.dependancy(depends=['test_read_headers', 'test_read_data'])
def test_deepcopy(instances):
    sac1, _ = instances
    sac5 = copy.deepcopy(sac1)
    assert sac1.data == sac5.data
    assert sac1.e == sac5.e
    sac5.delta = sac1.delta * 2
    assert sac1.e != sac5.e
