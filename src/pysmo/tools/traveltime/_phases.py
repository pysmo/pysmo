"""Membership in the IASPEI Standard Seismic Phase List."""

import re
import tomllib
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

_PHASE_FILE = Path(__file__).resolve().parent / "data" / "iaspei_phases.toml"
# Depth-phase templates (`pP<y>`) only extend phases from these sections.
_BODY_SECTIONS = frozenset({"crustal", "mantle", "core"})
_SECTIONS = _BODY_SECTIONS | {"depth", "surface", "acoustic", "unidentified"}
_PLACEHOLDER = re.compile(r"<([Nzy])>")
_NUMBER = "[1-9][0-9]*"


class _PhaseList(NamedTuple):
    names: frozenset[str]
    """Listed names without placeholders, standard and alternative."""
    alternatives: dict[str, str]
    """Acceptable alternative name to the standard name it stands for."""
    old: dict[str, str | None]
    """Old name to the standard name that replaced it, if there is one."""
    any_phase: re.Pattern[str]
    """Every non-depth entry, templates expanded."""
    body_phase: re.Pattern[str]
    """Entries of the crustal, mantle and core sections."""
    depth_heads: tuple[str, ...]
    """Depth-phase templates without `<y>`, e.g. `pP`, `pwP`."""


def _to_regex(entry: str) -> str:
    parts = _PLACEHOLDER.split(entry)
    # re.split with one group alternates literal text and placeholder names.
    return "".join(
        re.escape(part) if i % 2 == 0 else _NUMBER for i, part in enumerate(parts)
    )


def _strings(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{_PHASE_FILE.name}: {where} must be a list of strings.")
    return value


def _mapping(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(v, str) for v in value.values()
    ):
        raise ValueError(f"{_PHASE_FILE.name}: {where} must map names to names.")
    return value


@cache
def _load() -> _PhaseList:
    data = tomllib.loads(_PHASE_FILE.read_text())
    if set(data) != _SECTIONS | {"old"}:
        raise ValueError(f"{_PHASE_FILE.name}: unexpected sections {sorted(data)}.")
    for section, table in data.items():
        allowed = {
            "old": {"replaced", "unreplaced"},
            "depth": {"names"},
        }.get(section, {"names", "alternatives"})
        if not set(table) <= allowed:
            raise ValueError(
                f"{_PHASE_FILE.name}: unexpected keys in [{section}]: "
                + f"{sorted(set(table) - allowed)}."
            )
    old_table = data.pop("old")
    old: dict[str, str | None] = dict.fromkeys(
        _strings(old_table.get("unreplaced"), "old.unreplaced")
    )
    old.update(_mapping(old_table.get("replaced"), "old.replaced"))

    depth = _strings(data.pop("depth").get("names"), "depth.names")
    if any(not head.endswith("<y>") or "<" in head[:-3] for head in depth):
        raise ValueError(f"{_PHASE_FILE.name}: depth names must end in <y>.")

    names: set[str] = set()
    alternatives: dict[str, str] = {}
    any_entries: list[str] = []
    body_entries: list[str] = []
    for section, table in data.items():
        section_alternatives = _mapping(
            table.get("alternatives", {}), f"{section}.alternatives"
        )
        alternatives.update(section_alternatives)
        for name in [
            *_strings(table.get("names"), f"{section}.names"),
            *section_alternatives,
        ]:
            if "<y>" in name:
                raise ValueError(f"{_PHASE_FILE.name}: <y> outside [depth]: {name}.")
            if "<" not in name:
                names.add(name)
            any_entries.append(_to_regex(name))
            if section in _BODY_SECTIONS:
                body_entries.append(_to_regex(name))
    return _PhaseList(
        names=frozenset(names),
        alternatives=alternatives,
        old=old,
        any_phase=re.compile("|".join(any_entries)),
        body_phase=re.compile("|".join(body_entries)),
        depth_heads=tuple(head[:-3] for head in depth),
    )


def standard_phases() -> frozenset[str]:
    """The fixed names in the IASPEI Standard Seismic Phase List.

    The set holds the standard names in the list adopted by IASPEI in
    2003, plus their acceptable alternatives (e.g. `PKIKP` for `PKPdf`).

    Names built from the list's templates, such as `PmP2`, `P410+P`, and
    `pPKP`, are not in the set. There is no fixed number of them.
    [`is_standard_phase`][pysmo.tools.traveltime.is_standard_phase]
    recognises them.

    A standard name is not necessarily one
    [`travel_times`][pysmo.tools.traveltime.travel_times] computes. Those
    are the [`Phase`][pysmo.tools.traveltime.Phase] names.

    Returns:
        Fixed names in the list.

    Examples:
        ```python
        >>> from pysmo.tools.traveltime import standard_phases
        >>> "Pdif" in standard_phases()
        True
        >>> "Pdiff" in standard_phases()
        False
        >>>
        ```
    """
    return _load().names


def is_standard_phase(name: str) -> bool:
    """Whether a name is in the IASPEI Standard Seismic Phase List.

    Checks `name` against the list adopted by IASPEI in 2003. Acceptable
    alternative names, such as `PKIKP` for `PKPdf`, count as standard.
    So do names built from the list's templates:

    - A number of legs or reflections, as a positive integer (`PmP2`,
      `ScS3`).
    - A discontinuity depth, as a positive whole number of km (`P410+P`,
      `P660-P`).
    - Depth phases (`pP`, `pPKP`, `sSdif`, `pwP`). Each is a near-source
      reflection before a crustal, mantle, or core phase that starts
      with the same leg.

    Names the list calls old (`Pdiff`, `PKP1`) are not standard, even
    where a template matches them. The amplitude measurement codes
    (`IAML`, `END`) are not standard either.

    Matching is exact and case-sensitive. Whitespace is not removed. A
    Unicode minus sign (U+2212) counts as `-`.

    A name that is not in the list is not necessarily invalid. The list
    does not name every possible phase. A standard name is not
    necessarily one [`travel_times`][pysmo.tools.traveltime.travel_times]
    computes. Those are the [`Phase`][pysmo.tools.traveltime.Phase] names.

    Args:
        name: Phase name.

    Returns:
        Whether `name` is in the list.

    Examples:
        ```python
        >>> from pysmo.tools.traveltime import is_standard_phase
        >>> is_standard_phase("PKIKP")
        True
        >>> is_standard_phase("pPKP")
        True
        >>> is_standard_phase("P410+P")
        True
        >>> is_standard_phase("Pdiff")
        False
        >>>
        ```

    References:
        Storchak, D. A., J. Schweitzer, and P. Bormann. “The IASPEI Standard
        Seismic Phase List.” Seismological Research Letters, vol. 74, no. 6,
        2003, pp. 761–72, <https://doi.org/10.1785/gssrl.74.6.761>.
    """
    phases = _load()
    name = name.replace("\N{MINUS SIGN}", "-")
    if name in phases.old:
        return False
    if phases.any_phase.fullmatch(name):
        return True
    return any(
        name.startswith(head)
        and phases.body_phase.fullmatch(head[-1] + name[len(head) :]) is not None
        for head in phases.depth_heads
    )
