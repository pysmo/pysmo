"""
Run tests for the SacIO class
"""

import os
import tempfile
import shutil
import copy
import pickle
import pytest
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
    Define temporary files for testing.
    - tmpfile1: copy of reference file, which is not modified during test
    - tmpfile2: copy of reference file, which is modified during test
    - tmpfile3: used to write a new sac file
    - tmpfile4: used to test pickling
    - tmpfile_special_IB: copy of sacfile with IZTYPE=IB
    """
    orgfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    tmpfile1 = os.path.join(tmpdir, 'tmpfile1.sac')
    tmpfile2 = os.path.join(tmpdir, 'tmpfile2.sac')
    tmpfile3 = os.path.join(tmpdir, 'tmpfile2.sac')
    tmpfile4 = os.path.join(tmpdir, 'tmpfile4.pickle')
    shutil.copyfile(orgfile, tmpfile1)
    shutil.copyfile(orgfile, tmpfile2)
    orgfile_special_IB = os.path.join(os.path.dirname(__file__),
                                      'testfile_iztype_is_IB.sac')
    tmpfile_special_IB = os.path.join(tmpdir, 'tmpfile4.pickle')
    shutil.copyfile(orgfile_special_IB, tmpfile_special_IB)
    return tmpfile1, tmpfile2, tmpfile3, tmpfile4, tmpfile_special_IB


@pytest.fixture()
def instances(tmpfiles):
    """Copy reference sac file to tmpdir"""
    tmpfile1, tmpfile2, _, _, tmpfile_special_IB = tmpfiles
    return SacIO.from_file(tmpfile1), SacIO.from_file(tmpfile2),\
        SacIO.from_file(tmpfile_special_IB)


def test_is_sacio_type(instances):
    """
    Test if a SacIO instance is created.
    """
    for sac_instance in instances:
        assert isinstance(sac_instance, SacIO)


@pytest.mark.depends(on=['test_is_sacio_type', 'test_read_data'])
def test_read_headers(instances):
    """
    Read all SAC headers from a test file
    """
    sac, *_, sac_iztype_IS_IB = instances
    assert sac.npts == 180000
    assert sac.b == pytest.approx(-63.34000015258789)
    assert sac.e == pytest.approx(3536.639892578125)
    assert sac.iftype == 'time'
    assert sac.leven is True
    assert pytest.approx(sac.delta) == 0.02
    assert sac.odelta is None
    assert sac.idep == 'unkn'
    assert sac.depmin == 451
    assert sac.depmax == 4178
    assert sac.depmen == pytest.approx(2323.753022222222)
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
    assert sac.kzdate == '2005-03-02'
    # kztime is a derived header
    assert sac.kztime == '07:24:05.500'
    assert sac.iztype == 'o'
    assert sac_iztype_IS_IB.iztype == 'b'
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
    assert sac.kstnm == 'VOH01'
    assert sac.cmpaz == 0
    assert sac.cmpinc == 0
    assert sac.istreg is None
    assert sac.stla == pytest.approx(-48.46787643432617)
    assert sac.stlo == pytest.approx(-72.56145477294922)
    assert sac.stel is None
    assert sac.stdp is None
    assert sac.kevnm == '050600723BHZ'
    assert sac.ievreg is None
    assert sac.evla == pytest.approx(-31.465999603271484)
    assert sac.evlo == pytest.approx(-71.71800231933594)
    assert sac.evel is None
    assert sac.evdp == 26
    assert sac.ievtyp == 'quake'
    assert sac.khole == ''
    assert sac.dist is None
    assert sac.az is None
    assert sac.baz is None
    assert sac.gcarc is None
    assert sac.lovrok is True
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
    assert sac.user8 == pytest.approx(5.199999809265137)
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
    assert sac.nwfid is None
    assert sac.iinst is None
    assert sac.lpspol is True
    assert sac.lcalda is True
    assert sac.kcmpnm == 'BHZ'
    assert sac.knetwk == 'YJ'
    assert sac.mag is None
    assert sac.imagtyp is None
    assert sac.imagsrc is None
    # try reading non-existing header
    with pytest.raises(AttributeError):
        _ = sac.nonexistingheader


@pytest.mark.depends(on=['test_is_sacio_type'])
def test_read_data(instances):
    """
    Test reading data.
    """
    sac, *_ = instances
    assert sac.data[:10] == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0, 2407.0,
                             2378.0, 2358.0, 2398.0, 2331.0]


@pytest.mark.depends(on=['test_read_headers'])
def test_change_headers(instances):
    """
    Test changing header values
    """

    sac1, sac2, *_ = instances

    iftype_valid = 'time'
    iftype_invalid = 'asdfasdf'

    # set iftype to a valid value
    sac2.iftype = iftype_valid
    assert sac2.iftype == iftype_valid

    # set iftype to an invalid value
    with pytest.raises(ValueError):
        sac2.iftype = iftype_invalid

    # Try setting a header that should only accept strings to a boolean
    with pytest.raises(ValueError):
        sac2.kuser0 = True

    # Try setting a string that is too long
    with pytest.raises(ValueError):
        sac2.kuser0 = 'too long string'

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


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_change_data(instances):
    """
    Test changing data
    """
    _, sac2, *_ = instances
    newdata = [132, 232, 3465, 111]
    sac2.data = newdata
    assert sac2.data == newdata
    assert sac2.depmin == min(newdata)
    assert sac2.depmax == max(newdata)
    assert sac2.depmen == sum(newdata)/sac2.npts


@pytest.mark.depends(on=['test_change_headers', 'test_change_data'])
def test_write_to_file(instances, tmpfiles):
    sac1, *_ = instances
    _, _, tmpfile3, *_ = tmpfiles
    sac1.write(tmpfile3)
    sac3 = SacIO.from_file(tmpfile3)
    assert sac1.data == sac3.data
    assert sac1.b == sac3.b


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_pickling(instances, tmpfiles):
    sac1, *_ = instances
    _, _, _, tmpfile4, *_ = tmpfiles
    with open(tmpfile4, "wb") as output_file:
        pickle.dump(sac1, output_file)
    with open(tmpfile4, "rb") as input_file:
        sac4 = pickle.load(input_file)
    assert sac1.data == sac4.data
    assert sac1.b == sac4.b


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_deepcopy(instances):
    sac1, *_ = instances
    sac5 = copy.deepcopy(sac1)
    assert sac1.data == sac5.data
    assert sac1.e == sac5.e
    sac5.delta = sac1.delta * 2
    assert sac1.e != sac5.e


def test_file_and_data(tmpdir):
    orgfile_special_IB = os.path.join(os.path.dirname(__file__),
                                      'testfile_iztype_is_IB.sac')
    tmpfile5 = os.path.join(tmpdir, 'tmpfile5.sac')
    shutil.copyfile(orgfile_special_IB, tmpfile5)

    from_file = SacIO.from_file(tmpfile5)
    with open(tmpfile5, "rb") as f:
        from_data = SacIO.from_data(f.read())

    assert from_file.npts == from_data.npts
    assert from_file.b == from_data.b
    assert from_file.e == from_data.e
    assert from_file.iftype == from_data.iftype
    assert from_file.leven == from_data.leven
    assert from_file.delta == from_data.delta
    assert from_file.odelta == from_data.odelta
    assert from_file.idep == from_data.idep
    assert from_file.depmin == from_data.depmin
    assert from_file.depmax == from_data.depmax
    assert from_file.depmen == from_data.depmen
    assert from_file.o == from_data.o
    assert from_file.a == from_data.a
    assert from_file.t0 == from_data.t0
    assert from_file.t1 == from_data.t1 
    assert from_file.t2 == from_data.t2 
    assert from_file.t3 == from_data.t3 
    assert from_file.t4 == from_data.t4 
    assert from_file.t5 == from_data.t5 
    assert from_file.t6 == from_data.t6 
    assert from_file.t7 == from_data.t7 
    assert from_file.t8 == from_data.t8 
    assert from_file.t9 == from_data.t9 
    assert from_file.f == from_data.f
    # kzdate is a derived header
    assert from_file.kzdate == from_data.kzdate
    # kztime is a derived header
    assert from_file.kztime == from_data.kztime
    assert from_file.iztype == from_data.iztype
    assert from_file.kinst == from_data.kinst
    assert from_file.resp0 == from_data.resp0
    assert from_file.resp1 == from_data.resp1
    assert from_file.resp2 == from_data.resp2 
    assert from_file.resp3 == from_data.resp3
    assert from_file.resp4 == from_data.resp4
    assert from_file.resp5 == from_data.resp5
    assert from_file.resp6 == from_data.resp6
    assert from_file.resp7 == from_data.resp7
    assert from_file.resp8 == from_data.resp8
    assert from_file.resp9 == from_data.resp9
    assert from_file.kdatrd == from_data.kdatrd
    assert from_file.kstnm == from_data.kstnm
    assert from_file.cmpaz == from_data.cmpaz
    assert from_file.cmpinc == from_data.cmpinc
    assert from_file.istreg == from_data.istreg
    assert from_file.stla == from_data.stla
    assert from_file.stlo == from_data.stlo
    assert from_file.stel == from_data.stel
    assert from_file.stdp == from_data.stdp
    assert from_file.kevnm == from_data.kevnm
    assert from_file.ievreg == from_data.ievreg
    assert from_file.evla == from_data.evla
    assert from_file.evlo == from_data.evlo
    assert from_file.evel == from_data.evel
    assert from_file.evdp == from_data.evdp
    assert from_file.ievtyp == from_data.ievtyp
    assert from_file.khole == from_data.khole
    assert from_file.dist == from_data.dist
    assert from_file.az == from_data.az
    assert from_file.baz == from_data.baz
    assert from_file.gcarc == from_data.gcarc
    assert from_file.lovrok == from_data.lovrok
    assert from_file.iqual == from_data.iqual
    assert from_file.isynth == from_data.isynth
    assert from_file.user0 == from_data.user0
    assert from_file.user1 == from_data.user1
    assert from_file.user2 == from_data.user2
    assert from_file.user3 == from_data.user3
    assert from_file.user4 == from_data.user4
    assert from_file.user5 == from_data.user5
    assert from_file.user6 == from_data.user6
    assert from_file.user7 == from_data.user7
    assert from_file.user8 == from_data.user8
    assert from_file.user9 == from_data.user9
    assert from_file.kuser0 == from_data.kuser0
    assert from_file.kuser1 == from_data.kuser1
    assert from_file.kuser2 == from_data.kuser2
    assert from_file.nxsize == from_data.nxsize
    assert from_file.xminimum == from_data.xminimum
    assert from_file.xmaximum == from_data.xmaximum
    assert from_file.nysize == from_data.nysize
    assert from_file.yminimum == from_data.yminimum
    assert from_file.ymaximum == from_data.ymaximum
    assert from_file.nvhdr == from_data.nvhdr
    assert from_file.scale == from_data.scale
    assert from_file.norid == from_data.norid
    assert from_file.nevid == from_data.nevid
    assert from_file.nwfid == from_data.nwfid
    assert from_file.iinst == from_data.iinst
    assert from_file.lpspol == from_data.lpspol
    assert from_file.lcalda == from_data.lcalda
    assert from_file.kcmpnm == from_data.kcmpnm
    assert from_file.knetwk == from_data.knetwk
    assert from_file.mag == from_data.mag
    assert from_file.imagtyp == from_data.imagtyp
    assert from_file.imagsrc == from_data.imagsrc
    assert from_file.data == from_data.data