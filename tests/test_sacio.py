"""
Run tests for the SacIO class
"""

import os
import tempfile
import shutil
import pytest
import copy
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
    """Copy reference sac file to tmpdir"""
    orgfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    tmpfile1 = os.path.join(tmpdir, 'tmpfile1.sac')
    tmpfile2 = os.path.join(tmpdir, 'tmpfile2.sac')
    tmpfile3 = os.path.join(tmpdir, 'tmpfile2.sac')
    shutil.copyfile(orgfile, tmpfile1)
    shutil.copyfile(orgfile, tmpfile2)
    return tmpfile1, tmpfile2, tmpfile3

@pytest.fixture()
def instances(tmpfiles):
    """Copy reference sac file to tmpdir"""
    tmpfile1, tmpfile2, _ = tmpfiles
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
    with pytest.raises(ValueError): sac.odelta
    assert sac.idep == 'unkn'
    assert sac.depmin == pytest.approx(-8293.0)
    assert sac.depmax == pytest.approx(3302.0)
    assert sac.depmen == pytest.approx(-572.200439453125)
    assert sac.o == pytest.approx(0.0)
    with pytest.raises(ValueError): sac.a
    with pytest.raises(ValueError): sac.t0
    with pytest.raises(ValueError): sac.t1
    with pytest.raises(ValueError): sac.t2
    with pytest.raises(ValueError): sac.t3
    with pytest.raises(ValueError): sac.t4
    with pytest.raises(ValueError): sac.t5
    with pytest.raises(ValueError): sac.t6
    with pytest.raises(ValueError): sac.t7
    with pytest.raises(ValueError): sac.t8
    with pytest.raises(ValueError): sac.t9
    with pytest.raises(ValueError): sac.f
    # kzdate is a derived header
    # kztime is a derived header
    assert sac.iztype == 'o'
    with pytest.raises(ValueError): sac.kinst
    with pytest.raises(ValueError): sac.resp0
    with pytest.raises(ValueError): sac.resp1
    with pytest.raises(ValueError): sac.resp2
    with pytest.raises(ValueError): sac.resp3
    with pytest.raises(ValueError): sac.resp4
    with pytest.raises(ValueError): sac.resp5
    with pytest.raises(ValueError): sac.resp6
    with pytest.raises(ValueError): sac.resp7
    with pytest.raises(ValueError): sac.resp8
    with pytest.raises(ValueError): sac.resp9
    with pytest.raises(ValueError): sac.kdatrd
    assert sac.kstnm == 'MEL01'
    assert sac.cmpaz == pytest.approx(0)
    assert sac.cmpinc == pytest.approx(90)
    with pytest.raises(ValueError): sac.istreg
    assert sac.stla == pytest.approx(-43.855464935302734)
    assert sac.stlo == pytest.approx(-73.74272155761719)
    with pytest.raises(ValueError): sac.stel
    with pytest.raises(ValueError): sac.stdp
    assert sac.kevnm == '043550359BHN'
    with pytest.raises(ValueError): sac.ievreg
    assert sac.evla == pytest.approx(-15.265999794006348)
    assert sac.evlo == pytest.approx(-75.20800018310547)
    with pytest.raises(ValueError): sac.evel
    assert sac.evdp == pytest.approx(30.899999618530273)
    assert sac.ievtyp == 'quake'
    assert sac.khole == ''
    assert sac.dist == pytest.approx(3172.399658203125)
    assert sac.az == pytest.approx(177.77978515625)
    assert sac.baz == pytest.approx(357.0372619628906)
    assert sac.gcarc == pytest.approx(28.522098541259766)
    assert sac.lovrok == True
    with pytest.raises(ValueError): sac.iqual
    with pytest.raises(ValueError): sac.isynth
    with pytest.raises(ValueError): sac.user0
    with pytest.raises(ValueError): sac.user1
    with pytest.raises(ValueError): sac.user2
    with pytest.raises(ValueError): sac.user3
    with pytest.raises(ValueError): sac.user4
    with pytest.raises(ValueError): sac.user5
    with pytest.raises(ValueError): sac.user6
    with pytest.raises(ValueError): sac.user7
    assert sac.user8 == pytest.approx(4.900000095367432)
    assert sac.user9 == pytest.approx(5.000000)
    with pytest.raises(ValueError): sac.kuser0
    with pytest.raises(ValueError): sac.kuser1
    with pytest.raises(ValueError): sac.kuser2
    with pytest.raises(ValueError): sac.nxsize
    with pytest.raises(ValueError): sac.xminimum
    with pytest.raises(ValueError): sac.xmaximum
    with pytest.raises(ValueError): sac.nysize
    with pytest.raises(ValueError): sac.yminimum
    with pytest.raises(ValueError): sac.ymaximum
    assert sac.nvhdr == 6
    with pytest.raises(ValueError): sac.scale
    assert sac.norid == 0
    assert sac.nevid == 0
    assert sac.nwfid == 13
    with pytest.raises(ValueError): sac.iinst
    assert sac.lpspol == True
    assert sac.lcalda == True
    assert sac.kcmpnm == 'BHN'
    assert sac.knetwk == 'YJ'
    with pytest.raises(ValueError): sac.mag
    with pytest.raises(ValueError): sac.imagtyp
    with pytest.raises(ValueError): sac.imagsrc
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
    sac1.iftype = iftype_valid
    assert sac1.iftype == iftype_valid

    # set iftype to an invalid value
    with pytest.raises(ValueError): sac1.iftype = iftype_invalid

    # Try setting a header that should only accept strings to a boolean
    with pytest.raises(ValueError): sac1.kuser0 = True

    # Try setting a string that is too long
    with pytest.raises(ValueError): sac1.kuser0 = 'too long string'

    # Are trailing spaces removed?
    sac1.kuser0 = 'aaaa   '
    assert sac1.kuser0 == 'aaaa'

    # Does changing header fields in one instance effect another?
    delta_old = sac1.delta
    sac1.delta = 2 * delta_old
    assert sac1.delta == pytest.approx(2 * delta_old)
    assert sac2.delta == pytest.approx(delta_old)

    # has the end time changed by changing delta?
    assert sac1.e != sac2.e

@pytest.mark.dependancy(depends=['test_read_headers', 'test_read_data'])
def test_change_data(instances):
    """
    Test changing data
    """
    sac1, _ = instances
    newdata = [132, 232, 3465, 111]
    olddata = sac1.data
    sac1.data = newdata
    assert sac1.data == newdata
    assert sac1.depmin == min(newdata)
    assert sac1.depmax == max(newdata)
    assert sac1.depmen == sum(newdata)/sac1.npts


@pytest.mark.dependancy(depends=['test_change_headers', 'test_change_data'])
def test_write_to_file(instances, tmpfiles):
    sac1, _ = instances
    _, _, tmpfile3 = tmpfiles
    sac1.write(tmpfile3)
    sac3 = SacIO.from_file(tmpfile3)
    assert sac1.data == sac3.data
    assert sac1.b == sac3.b
