"""Tests for pysmo.lib.io.SacIO."""

from beartype.roar import BeartypeCallHintParamViolation
from pysmo.lib.io import SacIO
from pandas import Timestamp, Timedelta
from datetime import timezone
from pathlib import Path
import copy
import pickle
import time
import pytest
import numpy as np
import numpy.testing as npt

# ─────────────────────────── Header tables ─────────────────────────────────
# Tests that set headers use fresh SacIO() instances (default iztype="unkn"),
# avoiding any iztype conflicts for time headers.

# (header, valid_float_value)
_FLOAT_HEADERS: list[tuple[str, float]] = [
    ("delta", 0.05),
    ("odelta", 0.05),
    ("b", 10.0),
    ("o", 10.0),
    ("a", 10.0),
    *[(f"t{i}", float(i + 1)) for i in range(10)],
    ("f", 100.0),
    ("stla", 45.0),
    ("stlo", 90.0),
    ("stel", 100.0),
    ("stdp", 50.0),
    ("evla", -30.0),
    ("evlo", -70.0),
    ("evel", 0.0),
    ("evdp", 10000.0),
    ("mag", 5.5),
    ("cmpaz", 90.0),
    ("cmpinc", 45.0),
    *[(f"user{i}", float(i)) for i in range(10)],
    *[(f"resp{i}", float(i) * 1e-6) for i in range(10)],
]

# Optional float headers (float | None) — can be cleared to None
_OPTIONAL_FLOAT_HEADERS: list[str] = [
    "odelta",
    "o",
    "a",
    *[f"t{i}" for i in range(10)],
    "f",
    "stla",
    "stlo",
    "stel",
    "stdp",
    "evla",
    "evlo",
    "evel",
    "evdp",
    "mag",
    "cmpaz",
    "cmpinc",
    *[f"user{i}" for i in range(10)],
    *[f"resp{i}" for i in range(10)],
]

# (header, valid_int_value)
_INT_HEADERS: list[tuple[str, int]] = [
    ("nzyear", 2020),
    ("nzjday", 100),
    ("nzhour", 12),
    ("nzmin", 30),
    ("nzsec", 45),
    ("nzmsec", 500),
    ("nvhdr", 6),
    ("norid", 1),
    ("nevid", 42),
    ("nwfid", 7),
]

# (header, valid_str_value, max_len)
_STR_HEADERS: list[tuple[str, str, int]] = [
    ("kstnm", "ABC", 8),
    ("kevnm", "test event", 16),
    ("khole", "00", 8),
    ("ko", "origin", 8),
    ("ka", "P", 8),
    *[(f"kt{i}", f"T{i}", 8) for i in range(10)],
    ("kf", "fini", 8),
    ("kuser0", "user0", 8),
    ("kuser1", "user1", 8),
    ("kuser2", "user2", 8),
    ("kcmpnm", "BHZ", 8),
    ("knetwk", "YJ", 8),
    ("kdatrd", "20200101", 8),
    ("kinst", "GPS", 8),
    ("iinst", "GPS", 4),
    ("istreg", "EU", 4),
    ("ievreg", "WA", 4),
]

_BOOL_HEADERS: list[str] = ["leven", "lovrok", "lpspol"]

# (header, valid_enum_string)
_ENUM_HEADERS: list[tuple[str, str]] = [
    ("iftype", "time"),
    ("idep", "unkn"),
    ("iztype", "unkn"),
    ("ievtyp", "quake"),
    ("iqual", "good"),
    ("isynth", "rldta"),
    ("imagtyp", "mb"),
    ("imagsrc", "neic"),
    ("ibody", "earth"),
]

# Read-only computed properties (no setter)
_READONLY_ATTRS: list[str] = [
    "npts",
    "e",
    "depmin",
    "depmax",
    "depmen",
    "dist",
    "az",
    "baz",
    "gcarc",
    "nxsize",
    "nysize",
    "xminimum",
    "xmaximum",
    "yminimum",
    "ymaximum",
    "lcalda",
    "kzdate",
    "kztime",
]


# ─────────────────────────── Basic tests ───────────────────────────────────


def test_create_instance() -> None:
    sac = SacIO()
    assert isinstance(sac, SacIO)


@pytest.mark.depends(on=["test_create_instance"])
def test_defaults() -> None:
    sac = SacIO()
    assert sac.b == 0


@pytest.mark.depends(on=["test_create_instance"])
def test_ref_datetime() -> None:
    sac = SacIO()
    assert sac.kzdate is None
    assert sac.kztime is None
    assert sac.ref_datetime is None
    now = Timestamp.now(timezone.utc)
    sac.ref_datetime = now
    now += Timedelta(microseconds=500)
    assert sac.ref_datetime.isoformat(timespec="milliseconds") == now.isoformat(  # type: ignore
        timespec="milliseconds"
    )


@pytest.mark.depends(on=["test_create_instance"])
def test_create_instance_from_file(sacfile: Path, sacfile_no_b: Path) -> None:
    sac = SacIO.from_file(sacfile)
    assert isinstance(sac, SacIO)
    with pytest.raises(RuntimeError):
        SacIO.from_file(sacfile_no_b)


@pytest.mark.depends(on=["test_create_instance"])
def test_write_to_file(empty_file: Path) -> None:
    sac = SacIO()
    sac.write(empty_file)
    sac = SacIO.from_file(empty_file)
    assert isinstance(sac, SacIO)

    random_data = np.random.rand(1000)
    sac = SacIO(b=21.1, data=random_data)
    sac.write(empty_file)
    sac = SacIO.from_file(empty_file)
    assert pytest.approx(sac.b) == 21.1
    npt.assert_allclose(sac.data, random_data)


# ─────────────────────────── Read all headers ──────────────────────────────


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_read_headers(sacfile: Path) -> None:
    """Read all SacIO headers from a test file."""
    sac = SacIO.from_file(sacfile)
    assert sac.npts == 180000
    assert sac.b == pytest.approx(-63.34000015258789)
    assert sac.e == pytest.approx(3536.639892578125)
    assert sac.iftype == "time"
    assert sac.leven is True
    assert pytest.approx(sac.delta) == 0.02
    assert sac.odelta is None
    assert sac.idep == "unkn"
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
    assert sac.kzdate == "2005-03-01"
    assert sac.kztime == "07:24:05.500"
    assert sac.iztype == "o"
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
    assert sac.kstnm == "VOH01"
    assert sac.cmpaz == 0
    assert sac.cmpinc == 0
    assert sac.istreg is None
    assert sac.stla == pytest.approx(-48.46787643432617)
    assert sac.stlo == pytest.approx(-72.56145477294922)
    assert sac.stel is None
    assert sac.stdp is None
    assert sac.kevnm == "050600723BHZ"
    assert sac.ievreg is None
    assert sac.evla == pytest.approx(-31.465999603271484)
    assert sac.evlo == pytest.approx(-71.71800231933594)
    assert sac.evel is None
    assert sac.evdp == 26
    assert sac.ievtyp == "quake"
    assert sac.khole == ""
    assert sac.dist == pytest.approx(1889.1549940066523)
    assert sac.az == pytest.approx(2.4677533885335987)
    assert sac.baz == pytest.approx(181.9199258637492)
    assert sac.gcarc == pytest.approx(17.013879929551447)
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
    assert sac.norid == 0
    assert sac.nevid == 0
    assert sac.nwfid is None
    assert sac.iinst is None
    assert sac.lpspol is True
    assert sac.lcalda is True
    assert sac.kcmpnm == "BHZ"
    assert sac.knetwk == "YJ"
    assert sac.mag is None
    assert sac.imagtyp is None
    assert sac.imagsrc is None
    assert sac.nzyear == 2005
    assert sac.nzjday == 60
    assert sac.nzhour == 7
    assert sac.nzmin == 24
    assert sac.nzsec == 5
    assert sac.nzmsec == 500
    with pytest.raises(AttributeError):
        _ = sac.nonexistingheader  # type: ignore[attr-defined]


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_v6_v7(sacfile_v6: Path, sacfile_v7: Path) -> None:
    sac6 = SacIO.from_file(sacfile_v6)
    sac7 = SacIO.from_file(sacfile_v7)
    assert sac6.nvhdr == 6
    assert sac7.nvhdr == 7
    sac7.write(sacfile_v7)
    sac7 = SacIO.from_file(sacfile_v7)


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_sacfile_IB(sacfile_IB: Path) -> None:
    sac = SacIO.from_file(sacfile_IB)
    assert sac.iztype == "b"


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_read_data(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    assert all(
        sac.data[:10]
        == [
            2302.0,
            2313.0,
            2345.0,
            2377.0,
            2375.0,
            2407.0,
            2378.0,
            2358.0,
            2398.0,
            2331.0,
        ]
    )


# ─────────────────────────── Write headers ─────────────────────────────────


@pytest.mark.parametrize(
    "header,value", _FLOAT_HEADERS, ids=[h for h, _ in _FLOAT_HEADERS]
)
def test_set_float_header(header: str, value: float) -> None:
    sac = SacIO()
    setattr(sac, header, value)
    assert getattr(sac, header) == pytest.approx(value)


@pytest.mark.parametrize("header", _OPTIONAL_FLOAT_HEADERS)
def test_clear_optional_float_header(header: str) -> None:
    sac = SacIO()
    setattr(sac, header, None)
    assert getattr(sac, header) is None


@pytest.mark.parametrize("header,value", _INT_HEADERS, ids=[h for h, _ in _INT_HEADERS])
def test_set_int_header(header: str, value: int) -> None:
    sac = SacIO()
    setattr(sac, header, value)
    assert getattr(sac, header) == value


@pytest.mark.parametrize("header", ["nwfid"])
def test_clear_optional_int_header(header: str) -> None:
    sac = SacIO()
    setattr(sac, header, None)
    assert getattr(sac, header) is None


@pytest.mark.parametrize(
    "header,value,_", _STR_HEADERS, ids=[h for h, _, __ in _STR_HEADERS]
)
def test_set_str_header(header: str, value: str, _: int) -> None:
    sac = SacIO()
    setattr(sac, header, value)
    assert getattr(sac, header) == value


@pytest.mark.parametrize(
    "header,_,__", _STR_HEADERS, ids=[h for h, _, __ in _STR_HEADERS]
)
def test_clear_optional_str_header(header: str, _: str, __: int) -> None:
    sac = SacIO()
    setattr(sac, header, None)
    assert getattr(sac, header) is None


@pytest.mark.parametrize("header", _BOOL_HEADERS)
def test_set_bool_header(header: str) -> None:
    sac = SacIO()
    current = getattr(sac, header)
    setattr(sac, header, not current)
    assert getattr(sac, header) == (not current)


@pytest.mark.parametrize(
    "header,value", _ENUM_HEADERS, ids=[h for h, _ in _ENUM_HEADERS]
)
def test_set_enum_header(header: str, value: str) -> None:
    sac = SacIO()
    setattr(sac, header, value)
    assert getattr(sac, header) == value


# ─────────────────────────── Type validation ───────────────────────────────


@pytest.mark.parametrize("header,_", _FLOAT_HEADERS, ids=[h for h, _ in _FLOAT_HEADERS])
def test_float_header_type_error(header: str, _: float) -> None:
    """Float headers with converters raise TypeError for non-numeric types."""
    sac = SacIO()
    with pytest.raises(TypeError):
        setattr(sac, header, [1.0])


@pytest.mark.parametrize("header,_", _INT_HEADERS, ids=[h for h, _ in _INT_HEADERS])
def test_int_header_type_error(header: str, _: int) -> None:
    """Int headers reject floats (no implicit truncation)."""
    sac = SacIO()
    with pytest.raises(TypeError):
        setattr(sac, header, 3.3)


@pytest.mark.parametrize(
    "header,_,__", _STR_HEADERS, ids=[h for h, _, __ in _STR_HEADERS]
)
def test_str_header_type_error(header: str, _: str, __: int) -> None:
    sac = SacIO()
    with pytest.raises(TypeError):
        setattr(sac, header, 123)


@pytest.mark.parametrize("header", _BOOL_HEADERS)
def test_bool_header_type_error(header: str) -> None:
    sac = SacIO()
    with pytest.raises(TypeError):
        setattr(sac, header, "abc")


# ─────────────────────────── Value validation ──────────────────────────────


@pytest.mark.parametrize(
    "header,over,under",
    [
        ("stla", 91.0, -91.0),
        ("stlo", 181.0, -181.0),
        ("evla", 91.0, -91.0),
        ("evlo", 181.0, -181.0),
    ],
)
def test_float_header_range_error(header: str, over: float, under: float) -> None:
    sac = SacIO()
    with pytest.raises(ValueError):
        setattr(sac, header, over)
    with pytest.raises(ValueError):
        setattr(sac, header, under)


@pytest.mark.parametrize(
    "header,_,max_len", _STR_HEADERS, ids=[h for h, _, __ in _STR_HEADERS]
)
def test_str_header_max_len(header: str, _: str, max_len: int) -> None:
    sac = SacIO()
    with pytest.raises(ValueError):
        setattr(sac, header, "x" * (max_len + 1))


@pytest.mark.parametrize("header,_", _ENUM_HEADERS, ids=[h for h, _ in _ENUM_HEADERS])
def test_invalid_enum_value(header: str, _: str) -> None:
    sac = SacIO()
    with pytest.raises(ValueError):
        setattr(sac, header, "not_a_valid_enum")


# ─────────────────────── Constructor type checking ─────────────────────────


def test_beartype_method_type_checking() -> None:
    """Beartype enforces types on explicitly annotated SacIO methods."""
    sac = SacIO()
    with pytest.raises(BeartypeCallHintParamViolation):
        sac.ref_datetime = "not_a_datetime"  # type: ignore
    with pytest.raises(BeartypeCallHintParamViolation):
        sac.change_all_times("ten")  # type: ignore


# ─────────────────────────── Read-only attrs ───────────────────────────────


@pytest.mark.parametrize("attr", _READONLY_ATTRS)
def test_readonly_attr(sacfile: Path, attr: str) -> None:
    sac = SacIO.from_file(sacfile)
    with pytest.raises(AttributeError):
        setattr(sac, attr, 0)


# ─────────────────────────── Misc behaviour ────────────────────────────────


@pytest.mark.depends(on=["test_read_headers"])
def test_change_data(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    newdata = np.array([132, 232, 3465, 111])
    sac.data = newdata
    assert all(sac.data == newdata)
    assert sac.depmin == min(newdata)
    assert sac.depmax == max(newdata)
    assert sac.depmen == sum(newdata) / sac.npts


@pytest.mark.depends(on=["test_read_headers"])
def test_iztype_prevents_zero_time_change(sacfile: Path) -> None:
    """Cannot change the header nominated as zero-time to a non-zero value."""
    sac = SacIO.from_file(sacfile)
    assert sac.iztype == "o"
    with pytest.raises(RuntimeError):
        sac.o = 123.0


@pytest.mark.depends(on=["test_read_headers"])
def test_change_all_times(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    sac2 = SacIO.from_file(sacfile)
    dtime = 10
    sac.a = 70.0
    sac2.a = 70.0
    sac2.change_all_times(dtime)
    assert sac.o == sac2.o - dtime  # type: ignore
    assert sac.b == sac2.b - dtime
    assert sac.a == sac2.a - dtime  # type: ignore


@pytest.mark.depends(on=["test_read_headers", "test_read_data"])
def test_pickling(sacfile: Path, empty_file: Path) -> None:
    sac = SacIO.from_file(sacfile)
    picklefile = empty_file
    with open(picklefile, "wb") as output_file:
        pickle.dump(sac, output_file)
    with open(picklefile, "rb") as input_file:
        sac2 = pickle.load(input_file)
    npt.assert_allclose(sac.data, sac2.data)
    assert sac.b == sac2.b


@pytest.mark.depends(on=["test_read_headers", "test_read_data"])
def test_deepcopy(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    sac2 = copy.deepcopy(sac)
    assert all(sac.data == sac2.data)
    assert sac.data is not sac2.data
    assert sac.e == sac2.e
    sac2.delta = sac.delta * 2
    assert sac.e != sac2.e


@pytest.mark.depends(on=["test_read_headers", "test_read_data"])
def test_file_and_buffer(sacfile: Path) -> None:
    from_file = SacIO.from_file(sacfile)
    with open(sacfile, "rb") as f:
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
    assert from_file.kzdate == from_buffer.kzdate
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
    assert from_file.nzyear == from_buffer.nzyear
    assert from_file.nzjday == from_buffer.nzjday
    assert from_file.nzhour == from_buffer.nzhour
    assert from_file.nzmin == from_buffer.nzmin
    assert from_file.nzsec == from_buffer.nzsec
    assert from_file.nzmsec == from_buffer.nzmsec
    assert all(from_file.data == from_buffer.data)


@pytest.mark.depends(on=["test_file_and_buffer"])
def test_iris_service() -> None:
    retries = 3
    for attempt in range(retries):
        try:
            mysac = SacIO.from_iris(
                net="C1",
                sta="VA01",
                cha="BHZ",
                loc="--",
                start="2021-03-22T13:00:00",
                duration=1 * 60 * 60,
                scale="AUTO",
                demean="true",
                force_single_result=True,
            )
            assert mysac.npts == 144001  # type: ignore
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(20)


@pytest.mark.depends(on=["test_file_and_buffer"])
def test_iris_service_params_error() -> None:
    try:
        SacIO.from_iris(
            net="XX",
            sta="XXXX",
            cha="XXX",
            loc="XX",
            start="2012-01-11T11:11:11",
            duration=1 * 60 * 60,
            scale="AUTO",
            demean="true",
            force_single_result=True,
        )
        assert False
    except Exception as error:
        assert str(error).startswith("Client error '404 '")


@pytest.mark.depends(on=["test_file_and_buffer"])
def test_iris_service_multi_result() -> None:
    retries = 3
    for attempt in range(retries):
        try:
            mysacs = SacIO.from_iris(
                net="IU",
                sta="MAKZ",
                cha="HHZ",
                loc="00",
                start="2015-09-09T15:00:00",
                duration=1 * 60 * 60,
                scale="AUTO",
                demean="true",
                force_single_result=False,
            )
            assert isinstance(mysacs, dict)
            assert len(mysacs) == 4
            data = [
                ("IU.MAKZ.00.HHZ.D.2015.252.150941.SAC", 36790),
                ("IU.MAKZ.00.HHZ.D.2015.252.152559.SAC", 39196),
                ("IU.MAKZ.00.HHZ.D.2015.252.154438.SAC", 40349),
                ("IU.MAKZ.00.HHZ.D.2015.252.155301.SAC", 37711),
            ]

            for name, npts in data:
                assert isinstance(mysacs[name], SacIO)
                assert mysacs[name].npts == npts
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(20)


@pytest.mark.depends(on=["test_file_and_buffer"])
def test_iris_service_multi_result_forced() -> None:
    retries = 3
    for attempt in range(retries):
        try:
            mysacs = SacIO.from_iris(
                net="IU",
                sta="MAKZ",
                cha="HHZ",
                loc="00",
                start="2015-09-09T15:00:00",
                duration=1 * 60 * 60,
                scale="AUTO",
                demean="true",
                force_single_result=True,
            )
            assert isinstance(mysacs, SacIO)
            assert mysacs.npts == 36790
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(20)
