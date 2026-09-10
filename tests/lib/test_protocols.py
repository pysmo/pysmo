import pytest

from pysmo.lib.protocols import (
    has_protocol_members,
    missing_protocol_members,
    satisfies_protocol,
)


def test_missing_protocol_members() -> None:
    from pysmo import Location

    class HasCoords:
        latitude = 1.0
        longitude = 2.0

    class NoLongitude:
        latitude = 1.0

    assert missing_protocol_members(HasCoords, Location) == []
    assert missing_protocol_members(NoLongitude, Location) == ["longitude"]


def test_has_protocol_members() -> None:
    from pysmo import Location

    class HasCoords:
        latitude = 1.0
        longitude = 2.0

    class NoLongitude:
        latitude = 1.0

    assert has_protocol_members(HasCoords, Location)
    assert not has_protocol_members(NoLongitude, Location)


def test_missing_protocol_members_counts_raising_getter_as_present() -> None:
    from pysmo import Location

    class BrokenCoords:
        @property
        def latitude(self) -> float:
            raise TypeError("no coordinates")

        @property
        def longitude(self) -> float:
            raise TypeError("no coordinates")

    assert missing_protocol_members(BrokenCoords(), Location) == []


def test_satisfies_protocol_validator() -> None:
    from attrs import define, field

    from pysmo import Location

    @define
    class Wrapper:
        loc: Location = field(validator=satisfies_protocol(Location))

    class Coords:
        latitude = 1.0
        longitude = 2.0

    Wrapper(loc=Coords())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="must satisfy the Location protocol"):
        Wrapper(loc=object())  # type: ignore[arg-type]
