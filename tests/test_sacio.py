# from __future__ import annotations
"""
Run tests for the SacIO class
"""

import copy
import pickle
import pytest
from pysmo.io import _SacIO as SacIO


def test_is_sac_type(sacio_instances: tuple[SacIO, ...]) -> None:
    """
    Test if a SacIO instance is created.
    """
    for sacio_instance in sacio_instances:
        assert isinstance(sacio_instance, SacIO)


@pytest.mark.depends(on=['test_is_sac_type', 'test_read_data'])
def test_read_headers(sacio_instances: tuple) -> None:
    """
    Read all SacIO headers from a test file
    """
    sac, *_, sac_iztype_IS_IB = sacio_instances
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
    assert sac.kzdate == '2005-03-01'
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


@pytest.mark.depends(on=['test_is_sac_type'])
def test_read_data(sacio_instances: tuple[SacIO, ...]) -> None:
    """
    Test reading data.
    """
    sac, *_ = sacio_instances
    assert all(sac.data[:10] == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0, 2407.0, 2378.0, 2358.0, 2398.0, 2331.0])


@pytest.mark.depends(on=['test_read_headers'])
def test_change_headers(sacio_instances: tuple) -> None:
    """
    Test changing header values
    """

    sac1, sac2, *_ = sacio_instances

    iftype_valid = 'time'
    iftype_invalid = 'asdfasdf'

    # set iftype to a valid value
    sac2.iftype = iftype_valid
    assert sac2.iftype == iftype_valid

    # set iftype to an invalid value
    with pytest.raises(KeyError):
        sac2.iftype = iftype_invalid

    # Try setting a header that should only accept integers with something else
    with pytest.raises(TypeError):
        sac2.nzmsec = 3.3

    # ... same for floats
    with pytest.raises(TypeError):
        sac2.delta = "3.3"

    # ... same for strings
    with pytest.raises(TypeError):
        sac2.kuser0 = True

    # ... same for boolean
    with pytest.raises(TypeError):
        sac2.leven = "True"

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

    # try changing read only header
    with pytest.raises(RuntimeError):
        sac1.npts = 123


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_change_data(sacio_instances: tuple) -> None:
    """
    Test changing data
    """
    _, sac2, *_ = sacio_instances
    newdata = [132, 232, 3465, 111]
    sac2.data = newdata
    assert sac2.data == newdata
    assert sac2.depmin == min(newdata)
    assert sac2.depmax == max(newdata)
    assert sac2.depmen == sum(newdata)/sac2.npts


@pytest.mark.depends(on=['test_change_headers', 'test_change_data'])
def test_write_to_file(sacio_instances: tuple[SacIO, ...], sacfiles: tuple[str, ...]) -> None:
    sac1, _, sac_empty, *_ = sacio_instances
    _, _, tmpfile3, *_ = sacfiles
    sac1.write(tmpfile3)
    sac3 = SacIO.from_file(tmpfile3)
    assert all(sac1.data == sac3.data)
    assert sac1.b == sac3.b
    sac_empty.write(tmpfile3)


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_pickling(sacio_instances: tuple[SacIO, ...], picklefiles: tuple[str, ...]) -> None:
    sac1, *_ = sacio_instances
    picklefile, *_ = picklefiles
    with open(picklefile, "wb") as output_file:
        pickle.dump(sac1, output_file)
    with open(picklefile, "rb") as input_file:
        sac4 = pickle.load(input_file)
    assert all(sac1.data == sac4.data)
    assert sac1.b == sac4.b


@pytest.mark.depends(on=['test_read_headers', 'test_read_data', 'test_change_headers'])
def test_deepcopy(sacio_instances: tuple) -> None:
    sac1, *_ = sacio_instances
    sac5 = copy.deepcopy(sac1)
    assert all(sac1.data == sac5.data)
    assert sac1.e == sac5.e
    sac5.delta = sac1.delta * 2
    assert sac1.e != sac5.e


@pytest.mark.depends(on=['test_read_headers', 'test_read_data'])
def test_file_and_buffer(sacfiles: tuple[str, ...]) -> None:
    orgfile_special_IB = sacfiles[3]
    from_file = SacIO.from_file(orgfile_special_IB)
    with open(orgfile_special_IB, "rb") as f:
        from_buffer = SacIO.from_buffer(f.read())

    assert from_file.npts == from_buffer.npts
    assert from_file.b == from_buffer.b
    assert from_file.e == from_buffer.e
    assert from_file.iftype == from_buffer.iftype
    assert from_file.leven == from_buffer.leven
    assert from_file.delta == from_buffer.delta
    assert from_file.odelta == from_buffer.odelta
    assert from_file.idep == from_buffer.idep
    assert from_file.depmin == from_buffer.depmin
    assert from_file.depmax == from_buffer.depmax
    assert from_file.depmen == from_buffer.depmen
    assert from_file.o == from_buffer.o
    assert from_file.a == from_buffer.a
    assert from_file.t0 == from_buffer.t0
    assert from_file.t1 == from_buffer.t1
    assert from_file.t2 == from_buffer.t2
    assert from_file.t3 == from_buffer.t3
    assert from_file.t4 == from_buffer.t4
    assert from_file.t5 == from_buffer.t5
    assert from_file.t6 == from_buffer.t6
    assert from_file.t7 == from_buffer.t7
    assert from_file.t8 == from_buffer.t8
    assert from_file.t9 == from_buffer.t9
    assert from_file.f == from_buffer.f
    # kzdate is a derived header
    assert from_file.kzdate == from_buffer.kzdate
    # kztime is a derived header
    assert from_file.kztime == from_buffer.kztime
    assert from_file.iztype == from_buffer.iztype
    assert from_file.kinst == from_buffer.kinst
    assert from_file.resp0 == from_buffer.resp0
    assert from_file.resp1 == from_buffer.resp1
    assert from_file.resp2 == from_buffer.resp2
    assert from_file.resp3 == from_buffer.resp3
    assert from_file.resp4 == from_buffer.resp4
    assert from_file.resp5 == from_buffer.resp5
    assert from_file.resp6 == from_buffer.resp6
    assert from_file.resp7 == from_buffer.resp7
    assert from_file.resp8 == from_buffer.resp8
    assert from_file.resp9 == from_buffer.resp9
    assert from_file.kdatrd == from_buffer.kdatrd
    assert from_file.kstnm == from_buffer.kstnm
    assert from_file.cmpaz == from_buffer.cmpaz
    assert from_file.cmpinc == from_buffer.cmpinc
    assert from_file.istreg == from_buffer.istreg
    assert from_file.stla == from_buffer.stla
    assert from_file.stlo == from_buffer.stlo
    assert from_file.stel == from_buffer.stel
    assert from_file.stdp == from_buffer.stdp
    assert from_file.kevnm == from_buffer.kevnm
    assert from_file.ievreg == from_buffer.ievreg
    assert from_file.evla == from_buffer.evla
    assert from_file.evlo == from_buffer.evlo
    assert from_file.evel == from_buffer.evel
    assert from_file.evdp == from_buffer.evdp
    assert from_file.ievtyp == from_buffer.ievtyp
    assert from_file.khole == from_buffer.khole
    assert from_file.dist == from_buffer.dist
    assert from_file.az == from_buffer.az
    assert from_file.baz == from_buffer.baz
    assert from_file.gcarc == from_buffer.gcarc
    assert from_file.lovrok == from_buffer.lovrok
    assert from_file.iqual == from_buffer.iqual
    assert from_file.isynth == from_buffer.isynth
    assert from_file.user0 == from_buffer.user0
    assert from_file.user1 == from_buffer.user1
    assert from_file.user2 == from_buffer.user2
    assert from_file.user3 == from_buffer.user3
    assert from_file.user4 == from_buffer.user4
    assert from_file.user5 == from_buffer.user5
    assert from_file.user6 == from_buffer.user6
    assert from_file.user7 == from_buffer.user7
    assert from_file.user8 == from_buffer.user8
    assert from_file.user9 == from_buffer.user9
    assert from_file.kuser0 == from_buffer.kuser0
    assert from_file.kuser1 == from_buffer.kuser1
    assert from_file.kuser2 == from_buffer.kuser2
    assert from_file.nxsize == from_buffer.nxsize
    assert from_file.xminimum == from_buffer.xminimum
    assert from_file.xmaximum == from_buffer.xmaximum
    assert from_file.nysize == from_buffer.nysize
    assert from_file.yminimum == from_buffer.yminimum
    assert from_file.ymaximum == from_buffer.ymaximum
    assert from_file.nvhdr == from_buffer.nvhdr
    assert from_file.scale == from_buffer.scale
    assert from_file.norid == from_buffer.norid
    assert from_file.nevid == from_buffer.nevid
    assert from_file.nwfid == from_buffer.nwfid
    assert from_file.iinst == from_buffer.iinst
    assert from_file.lpspol == from_buffer.lpspol
    assert from_file.lcalda == from_buffer.lcalda
    assert from_file.kcmpnm == from_buffer.kcmpnm
    assert from_file.knetwk == from_buffer.knetwk
    assert from_file.mag == from_buffer.mag
    assert from_file.imagtyp == from_buffer.imagtyp
    assert from_file.imagsrc == from_buffer.imagsrc
    assert all(from_file.data == from_buffer.data)


@pytest.mark.depends(on=['test_file_and_buffer'])
def test_iris_service() -> None:
    mysac = SacIO.from_iris(
        net="C1",
        sta="VA01",
        cha="BHZ",
        loc="--",
        start="2021-03-22T13:00:00",
        duration=1 * 60 * 60,
        scale="AUTO",
        demean="true",
        force_single_result=True)
    assert mysac.npts == 144001  # type: ignore
