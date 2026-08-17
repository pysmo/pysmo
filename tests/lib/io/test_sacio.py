"""Tests for pysmo.lib.io.SacIO."""

import copy
import pickle
from datetime import timedelta, timezone
from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest
from syrupy.assertion import SnapshotAssertion

from pysmo.lib.io import SacIO

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

# iztype is read-only after construction (see test_iztype_is_read_only and
# test_change_ref_time), so it is excluded from the generic setter tests.
_ENUM_HEADERS_SETTABLE: list[tuple[str, str]] = [
    (h, v) for h, v in _ENUM_HEADERS if h != "iztype"
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
    now = pd.Timestamp.now(timezone.utc)
    sac.ref_datetime = now
    now += pd.Timedelta(microseconds=500)
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
def test_read_header_types(sacfile: Path) -> None:
    """Verify that reading headers from a file satisfies type contracts."""
    sac = SacIO.from_file(sacfile)

    for header, _ in _FLOAT_HEADERS:
        value = getattr(sac, header)
        assert value is None or isinstance(value, float | int), (
            f"Header '{header}' should be float|None, got {type(value)}"
        )

    for header, _ in _INT_HEADERS:
        value = getattr(sac, header)
        assert value is None or isinstance(value, int), (
            f"Header '{header}' should be int|None, got {type(value)}"
        )

    for header, _, _ in _STR_HEADERS:
        value = getattr(sac, header)
        assert value is None or isinstance(value, str), (
            f"Header '{header}' should be str|None, got {type(value)}"
        )

    for header in _BOOL_HEADERS:
        value = getattr(sac, header)
        assert value is None or isinstance(value, bool), (
            f"Header '{header}' should be bool|None, got {type(value)}"
        )

    for header, _ in _ENUM_HEADERS:
        value = getattr(sac, header)
        assert value is None or isinstance(value, str), (
            f"Header '{header}' should be str|None, got {type(value)}"
        )


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_read_headers_semantic(sacfile: Path) -> None:
    """Verify key header values that have seismological semantic significance."""
    sac = SacIO.from_file(sacfile)

    # Core timing & metadata
    assert sac.npts == 57465
    assert sac.delta == pytest.approx(0.05)
    assert sac.iftype == "time"
    assert sac.leven is True
    assert sac.kstnm == "ANMO"
    assert sac.knetwk == "IU"
    assert sac.kcmpnm == "BHZ"

    # Station & Event coordinates
    assert sac.stla == pytest.approx(34.945980072021484)
    assert sac.stlo == pytest.approx(-106.4571304321289)
    assert sac.evla == pytest.approx(-36.12200164794922)
    assert sac.evlo == pytest.approx(-72.89800262451172)

    # Computed / derived values
    assert sac.dist == pytest.approx(8603.325124418385)
    assert sac.gcarc == pytest.approx(77.63835363183948)

    with pytest.raises(AttributeError):
        _ = sac.nonexistingheader  # type: ignore[attr-defined]


@pytest.mark.depends(on=["test_create_instance_from_file"])
def test_read_headers_snapshot(sacfile: Path, snapshot: SnapshotAssertion) -> None:
    """Full header snapshot — catches regressions in SAC header reading."""
    sac = SacIO.from_file(sacfile)
    headers: dict[str, object] = {}
    for header, _ in _FLOAT_HEADERS:
        headers[header] = getattr(sac, header)
    for header, _ in _INT_HEADERS:
        headers[header] = getattr(sac, header)
    for header, _, _ in _STR_HEADERS:
        headers[header] = getattr(sac, header)
    for header in _BOOL_HEADERS:
        headers[header] = getattr(sac, header)
    for header, _ in _ENUM_HEADERS:
        headers[header] = getattr(sac, header)
    for attr in _READONLY_ATTRS:
        headers[attr] = getattr(sac, attr)

    # Round floating-point values to 6 decimal places to ensure cross-platform
    # snapshot stability (e.g. calculated spherical trig headers dist, gcarc).
    headers = {
        k: round(float(v), 6) if isinstance(v, (float, np.floating)) else v
        for k, v in headers.items()
    }

    assert headers == snapshot


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
            -47201.0,
            -47361.0,
            -47511.0,
            -47666.0,
            -47826.0,
            -47993.0,
            -48168.0,
            -48344.0,
            -48516.0,
            -48684.0,
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
    "header,value", _ENUM_HEADERS_SETTABLE, ids=[h for h, _ in _ENUM_HEADERS_SETTABLE]
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


@pytest.mark.parametrize(
    "header,_", _ENUM_HEADERS_SETTABLE, ids=[h for h, _ in _ENUM_HEADERS_SETTABLE]
)
def test_invalid_enum_value(header: str, _: str) -> None:
    sac = SacIO()
    with pytest.raises(ValueError):
        setattr(sac, header, "not_a_valid_enum")


def test_iztype_invalid_enum_value() -> None:
    """iztype's enum validator still runs at construction time."""
    with pytest.raises(ValueError):
        SacIO(iztype="not_a_valid_enum")


# ─────────────────────────── Read-only attrs ───────────────────────────────


@pytest.mark.parametrize("attr", _READONLY_ATTRS)
def test_readonly_attr(sacfile: Path, attr: str) -> None:
    sac = SacIO.from_file(sacfile)
    with pytest.raises(AttributeError):
        setattr(sac, attr, 0)


# ─────────────────────────── Misc behaviour ────────────────────────────────


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_change_data(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    newdata = np.array([132, 232, 3465, 111])
    sac.data = newdata
    assert all(sac.data == newdata)
    assert sac.depmin == min(newdata)
    assert sac.depmax == max(newdata)
    assert sac.depmen == sum(newdata) / sac.npts


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_iztype_prevents_zero_time_change() -> None:
    """Cannot change the header nominated as zero-time to a non-zero value."""
    sac = SacIO(iztype="o")
    sac.o = 0.0
    with pytest.raises(RuntimeError):
        sac.o = 123.0


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_iztype_is_read_only(sacfile: Path) -> None:
    """iztype can only be changed via change_ref_time."""
    sac = SacIO.from_file(sacfile)
    with pytest.raises(AttributeError):
        sac.iztype = "o"


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_change_ref_time(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    old_ref = sac.ref_datetime
    old_b = sac.b
    old_o = sac.o
    assert old_ref is not None
    assert old_o is not None

    sac.change_ref_time("o")

    assert sac.iztype == "o"
    new_ref = sac.ref_datetime
    new_o = sac.o
    new_b = sac.b
    assert new_ref is not None
    assert new_o is not None

    # 'o' lands within half a millisecond of 0 (ref_datetime only has
    # millisecond precision), not exactly on it.
    assert new_o == pytest.approx(0.0, abs=5e-4)

    # every header's absolute time is preserved exactly.
    assert new_ref + timedelta(seconds=new_o) == old_ref + timedelta(seconds=old_o)
    assert new_ref + timedelta(seconds=new_b) == old_ref + timedelta(seconds=old_b)


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_change_ref_time_invalid_header(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    with pytest.raises(ValueError):
        sac.change_ref_time("e")


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_change_ref_time_requires_ref_datetime() -> None:
    sac = SacIO()
    sac.o = 10.0
    with pytest.raises(ValueError):
        sac.change_ref_time("o")


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_change_ref_time_requires_header_value(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    assert sac.a is None
    with pytest.raises(ValueError):
        sac.change_ref_time("a")


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_read_after_change_ref_time(sacfile: Path) -> None:
    """Reloading a file must not raise because of a stale iztype-pinned
    header value left over from before the reload."""
    sac = SacIO.from_file(sacfile)
    sac.change_ref_time("o")
    assert sac.iztype == "o"

    sac.read(sacfile)

    assert sac.iztype == "unkn"
    assert sac.o == pytest.approx(-594.5390014648438)


@pytest.mark.depends(on=["test_read_headers_semantic"])
def test_read_resets_stale_optional_headers(sacfile: Path) -> None:
    """A header this file doesn't define must not keep a stale value from
    a previously loaded file when reusing an existing instance."""
    sac = SacIO.from_file(sacfile)
    sac.a = 123.0
    assert sac.a == 123.0

    sac.read(sacfile)

    assert sac.a is None


@pytest.mark.depends(on=["test_read_headers_semantic", "test_read_data"])
def test_pickling(sacfile: Path, empty_file: Path) -> None:
    sac = SacIO.from_file(sacfile)
    picklefile = empty_file
    with open(picklefile, "wb") as output_file:
        pickle.dump(sac, output_file)
    with open(picklefile, "rb") as input_file:
        sac2 = pickle.load(input_file)
    npt.assert_allclose(sac.data, sac2.data)
    assert sac.b == sac2.b


@pytest.mark.depends(on=["test_read_headers_semantic", "test_read_data"])
def test_deepcopy(sacfile: Path) -> None:
    sac = SacIO.from_file(sacfile)
    sac2 = copy.deepcopy(sac)
    assert all(sac.data == sac2.data)
    assert sac.data is not sac2.data
    assert sac.e == sac2.e
    sac2.delta = sac.delta * 2
    assert sac.e != sac2.e


@pytest.mark.depends(on=["test_read_headers_semantic", "test_read_data"])
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


def test_computed_geo_properties_with_zero_coordinates() -> None:
    """Zero-valued coordinates (equator/prime meridian) must not be treated as None."""
    sac = SacIO()
    # Place both station and event on the equator/prime meridian (lat=0, lon=0).
    sac.stla = 0.0
    sac.stlo = 0.0
    sac.evla = 0.0
    sac.evlo = 0.0
    # All four computed properties must return a number, not raise TypeError.
    assert isinstance(sac.dist, float)
    assert isinstance(sac.az, float)
    assert isinstance(sac.baz, float)
    assert isinstance(sac.gcarc, float)


def test_computed_geo_properties_raises_when_none() -> None:
    """dist/az/baz/gcarc must raise TypeError when any coordinate is genuinely None."""
    sac = SacIO()
    # All coordinates None (default).
    with pytest.raises(TypeError):
        _ = sac.dist
    with pytest.raises(TypeError):
        _ = sac.az
    with pytest.raises(TypeError):
        _ = sac.baz
    with pytest.raises(TypeError):
        _ = sac.gcarc

    # Partial None: stla set but stlo missing — must still raise.
    sac.stla = 0.0
    with pytest.raises(TypeError):
        _ = sac.dist
    with pytest.raises(TypeError):
        _ = sac.az
    with pytest.raises(TypeError):
        _ = sac.baz
    with pytest.raises(TypeError):
        _ = sac.gcarc
