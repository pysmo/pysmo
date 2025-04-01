from pysmo import (
    Location,
    MiniLocation,
    MiniLocationWithDepth,
    MiniEvent,
    MiniStation,
    LocationWithDepth,
    Event,
)


def test_proto2mini() -> None:
    from pysmo.lib.typing import proto2mini

    assert set(proto2mini(Location)) == set(
        [MiniLocation, MiniLocationWithDepth, MiniEvent, MiniStation]
    )


def test_matching_pysmo_types() -> None:
    from pysmo.lib.typing import matching_pysmo_types

    assert set(matching_pysmo_types(MiniEvent)) == set(
        [Location, LocationWithDepth, Event]
    )
