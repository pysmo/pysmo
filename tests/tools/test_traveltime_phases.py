"""Tests for the IASPEI standard phase list (pysmo.tools.traveltime)."""

import tomllib
from pathlib import Path
from typing import get_args

import pytest

from pysmo.tools.traveltime import Phase, _phases, is_standard_phase, standard_phases
from pysmo.tools.traveltime._phases import _PHASE_FILE, _load


@pytest.mark.parametrize(
    "name",
    [
        # Fixed names.
        "Pg",
        "Pn",
        "Lg",
        "PKiKP",
        "P'P'",
        "Pdif",
        "PKPdf",
        "SPdifKS",
        # Acceptable alternatives.
        "PKIKP",
        "P'",
        "S'",
        "P*",
        "SKPdifS",
        # <N> templates.
        "PmP2",
        "ScS3",
        "PcP12",
        "P'3",
        "PKP3",
        "P4KP",
        "PK2IKP",
        "S3KS",
        "G3",
        "R2",
        # <z> templates.
        "P410+P",
        "P410P",
        "S660S",
        "S660P",
        "P660S",
        "P660-P",
        "P660\N{MINUS SIGN}P",
        "S'660-S'",
        "P660-P'",
        # Depth phases.
        "pP",
        "pPKP",
        "pPcP",
        "pPcP2",
        "sP",
        "sPKP",
        "pS",
        "pScP",
        "pSKS",
        "pSP",
        "sSn",
        "sSdif",
        "sScS",
        "pwP",
        "pwPKP",
        "pmP",
        # Depth phases on templated phases, including templated alternatives.
        "pP410+P",
        "pPmP2",
        "pwP660-P",
        "pmP660\N{MINUS SIGN}P",
        "sS660-S",
        "sS660S",
        "sP660P",
        # Surface, acoustic and unidentified.
        "LR",
        "H",
        "TPg",
        "x",
        "Px",
    ],
)
def test_standard(name: str) -> None:
    assert is_standard_phase(name)


@pytest.mark.parametrize(
    "name",
    [
        # Old names.
        "Pdiff",
        "Sdiff",
        "PKP1",
        "PKP2",
        "PKhKP",
        "i",
        "e",
        "NULL",
        "P?",
        "(P)",
        # Amplitude measurement codes.
        "IAML",
        "AMs",
        "END",
        # Depth prefix before the wrong leg or a non-body phase.
        "pwS",
        "pmS",
        "ppP",
        "pPL",
        "pPx",
        # Template numbers.
        "PmP0",
        "PmP02",
        "P410.5+P",
        "P+P",
        # Typos, case and whitespace.
        "PKPP",
        "pkp",
        "PG",
        " P",
        "P ",
        "p",
        "",
    ],
)
def test_not_standard(name: str) -> None:
    assert not is_standard_phase(name)


def test_s660_minus_s_prime_is_not_standard() -> None:
    # The list has S'<z>-S' but not S<z>-S'.
    assert not is_standard_phase("S660-S'")


def test_standard_phases_are_fixed_names() -> None:
    names = standard_phases()
    assert {"Pdif", "PKIKP", "PKPdf", "P'", "x"} <= names
    assert not {"Pdiff", "IAML", "pP", "PmP2"} & names
    assert not any("<" in name for name in names)
    assert all(is_standard_phase(name) for name in names)


def test_alternatives_point_to_listed_entries() -> None:
    data = tomllib.loads(_PHASE_FILE.read_text())
    entries = {
        name
        for section, table in data.items()
        if section != "old"
        for name in table["names"]
    }
    phases = _load()
    assert phases.alternatives
    for alternative, standard in phases.alternatives.items():
        assert standard in entries
        assert standard not in phases.alternatives, alternative
    for name, replacement in phases.old.items():
        assert replacement is None or replacement in entries, name


_MINIMAL_PHASE_FILE = """
[crustal]
names = ["Pg"]
[mantle]
names = ["P"]
[core]
names = ["PKP"]
[depth]
names = ["pP<y>"]
[surface]
names = ["L"]
[acoustic]
names = ["H"]
[unidentified]
names = ["x"]
[old]
unreplaced = ["i"]
[old.replaced]
Pdiff = "Pdif"
"""


def test_minimal_phase_file_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "phases.toml"
    path.write_text(_MINIMAL_PHASE_FILE)
    monkeypatch.setattr(_phases, "_PHASE_FILE", path)
    assert _load.__wrapped__().names == {"Pg", "P", "PKP", "L", "H", "x"}


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('names = ["L"]', 'names = "L"', "must be a list of strings"),
        ('Pdiff = "Pdif"', "Pdiff = 1", "must map names to names"),
        ("[old]", "[extra]\nnames = []\n[old]", "unexpected sections"),
        ('names = ["L"]', 'name = ["L"]', "unexpected keys"),
        ('"pP<y>"', '"pP"', "must end in <y>"),
        ('"L"', '"L<y>"', "<y> outside"),
    ],
)
def test_malformed_phase_file_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, old: str, new: str, message: str
) -> None:
    path = tmp_path / "phases.toml"
    path.write_text(_MINIMAL_PHASE_FILE.replace(old, new, 1))
    monkeypatch.setattr(_phases, "_PHASE_FILE", path)
    with pytest.raises(ValueError, match=message):
        _load.__wrapped__()


def test_old_names_override_templates() -> None:
    # PKP2 also matches PKP<N> (P'2), but the list retires it as PKPab.
    assert not is_standard_phase("PKP2")
    assert is_standard_phase("PKP3")


@pytest.mark.parametrize("phase", get_args(Phase.__value__))
def test_computable_phases_are_standard(phase: str) -> None:
    assert is_standard_phase(phase)
