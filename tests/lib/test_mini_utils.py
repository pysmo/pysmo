from pysmo import (
    Event,
    Location,
    LocationWithDepth,
    MiniEvent,
    MiniLocation,
    MiniLocationWithDepth,
    MiniSeismogram,
    MiniStation,
    Seismogram,
    Station,
)


def test_proto2mini() -> None:
    from pysmo.lib.mini_utils import proto2mini

    assert set(proto2mini(Location)) == set(
        [MiniLocation, MiniLocationWithDepth, MiniEvent, MiniStation]
    )


def test_proto2mini_covers_disjoint_protocols() -> None:
    """proto2mini must include Minis for each protocol independently.

    Seismogram and Station are disjoint — no Mini satisfies both — so the
    results must be the union of each individual call.
    """
    from pysmo.lib.mini_utils import proto2mini

    seismogram_minis = set(proto2mini(Seismogram))
    station_minis = set(proto2mini(Station))

    assert MiniSeismogram in seismogram_minis
    assert MiniStation in station_minis
    # Sanity check they are indeed disjoint
    assert seismogram_minis.isdisjoint(station_minis)


def test_get_flattened_types_union() -> None:
    """_get_flattened_types must flatten a union into all its members."""
    from pysmo.lib.mini_utils import _get_flattened_types

    type SeismogramOrStation = Seismogram | Station

    result = _get_flattened_types(SeismogramOrStation)
    assert Seismogram in result
    assert Station in result
    assert len(result) == 2


def test_proto2mini_no_duplicates_overlapping_protocols() -> None:
    """Minis satisfying multiple protocols in a union must appear only once."""
    from pysmo.lib.mini_utils import proto2mini

    # MiniLocationWithDepth satisfies both Location and LocationWithDepth.
    # Passing a union alias exercises the deduplication path in proto2mini.
    type LocOrLocDepth = Location | LocationWithDepth

    result = proto2mini(LocOrLocDepth)  # type: ignore[arg-type]
    assert result.count(MiniLocationWithDepth) == 1


def test_matching_pysmo_types() -> None:
    from pysmo.lib.mini_utils import matching_pysmo_types

    assert set(matching_pysmo_types(MiniEvent)) == set(
        [Location, LocationWithDepth, Event]
    )
