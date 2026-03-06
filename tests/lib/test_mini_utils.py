from pysmo import (
    Event,
    Location,
    LocationWithDepth,
    MiniEvent,
    MiniLocation,
    MiniLocationWithDepth,
    MiniStation,
)


def test_proto2mini() -> None:
    from pysmo.lib.mini_utils import proto2mini

    assert set(proto2mini(Location)) == set(
        [MiniLocation, MiniLocationWithDepth, MiniEvent, MiniStation]
    )


def test_matching_pysmo_types() -> None:
    from pysmo.lib.mini_utils import matching_pysmo_types

    assert set(matching_pysmo_types(MiniEvent)) == set(
        [Location, LocationWithDepth, Event]
    )
