"""Tests for the in-house tau-p travel-time solver (pysmo.tools.traveltime)."""

from typing import cast, get_args

import pandas as pd
import pytest

from pysmo.tools.traveltime import Model, Phase, travel_times
from pysmo.tools.traveltime._model import _DATA_DIR
from pysmo.tools.traveltime._solver import _SUPPORTED_PHASES

# Reference travel times are TauP-origin IASP91 numbers (reproduced by
# obspy.taup); the solver matches them to within a few milliseconds. Each
# row is (source depth in km, epicentral distance in degrees, phase,
# reference travel time in seconds).
IAS91_REFERENCE: list[tuple[float, float, Phase, float]] = [
    (22.9, 2.5, "P", 39.241),
    (22.9, 5.0, "P", 73.610),
    (22.9, 60.0, "P", 604.654),
    (22.9, 90.0, "P", 777.560),
    (22.9, 98.0, "P", 814.081),
    (22.9, 2.5, "S", 69.732),
    (22.9, 5.0, "S", 131.524),
    (22.9, 60.0, "S", 1096.553),
    (0.0, 5.0, "P", 76.274),
    (0.0, 60.0, "P", 608.280),
    (0.0, 98.0, "P", 817.866),
    (0.0, 60.0, "S", 1102.731),
    (0.0, 5.0, "PcP", 512.468),
    (0.0, 60.0, "PcP", 654.204),
    (0.0, 98.0, "PcP", 817.868),
    (0.0, 5.0, "ScS", 937.777),
    (0.0, 60.0, "ScS", 1200.122),
    (0.0, 98.0, "ScS", 1505.864),
    (0.0, 5.0, "PcS", 724.971),
    (0.0, 60.0, "PcS", 896.531),
    (0.0, 5.0, "ScP", 724.971),
    (0.0, 60.0, "ScP", 896.531),
    (22.9, 5.0, "PcP", 508.575),
    (22.9, 60.0, "PcP", 650.398),
    (22.9, 98.0, "PcP", 814.083),
    (22.9, 5.0, "ScS", 931.054),
    (22.9, 60.0, "ScS", 1193.574),
    (22.9, 98.0, "ScS", 1499.362),
    (22.9, 5.0, "PcS", 721.079),
    (22.9, 60.0, "PcS", 892.746),
    (22.9, 5.0, "ScP", 718.247),
    (22.9, 60.0, "ScP", 889.868),
    (300.0, 5.0, "PcP", 474.526),
    (300.0, 60.0, "PcP", 617.918),
    (300.0, 90.0, "PcP", 746.484),
    (300.0, 5.0, "ScS", 869.391),
    (300.0, 60.0, "ScS", 1134.905),
    (300.0, 90.0, "ScS", 1374.947),
    (300.0, 5.0, "PcS", 687.046),
    (300.0, 5.0, "ScP", 656.563),
]

# The same matrix evaluated against the ak135 model; reference times are
# TauP-origin ak135 numbers (reproduced by obspy.taup). The solver matches
# them to within a few milliseconds, like the IASP91 rows. Geometries in
# the P triplication band (surface source, ~24-26 degrees) are left out:
# there the solver's single turning branch and TauP's first-arrival branch
# differ by design.
AK135_REFERENCE: list[tuple[float, float, Phase, float]] = [
    (22.9, 2.5, "P", 39.241),
    (22.9, 5.0, "P", 73.609),
    (22.9, 60.0, "P", 604.692),
    (22.9, 90.0, "P", 777.614),
    (22.9, 98.0, "P", 814.305),
    (22.9, 2.5, "S", 69.010),
    (22.9, 5.0, "S", 130.677),
    (22.9, 60.0, "S", 1095.897),
    (0.0, 5.0, "P", 76.274),
    (0.0, 60.0, "P", 608.319),
    (0.0, 98.0, "P", 818.087),
    (0.0, 60.0, "S", 1101.867),
    (0.0, 5.0, "PcP", 512.872),
    (0.0, 60.0, "PcP", 654.442),
    (0.0, 98.0, "PcP", 818.130),
    (0.0, 5.0, "ScS", 937.981),
    (0.0, 60.0, "ScS", 1200.149),
    (0.0, 98.0, "ScS", 1506.157),
    (0.0, 5.0, "PcS", 725.276),
    (0.0, 60.0, "PcS", 896.715),
    (0.0, 5.0, "ScP", 725.276),
    (0.0, 60.0, "ScP", 896.715),
    (22.9, 5.0, "PcP", 508.979),
    (22.9, 60.0, "PcP", 650.636),
    (22.9, 98.0, "PcP", 814.345),
    (22.9, 5.0, "ScS", 931.450),
    (22.9, 60.0, "ScS", 1193.798),
    (22.9, 98.0, "ScS", 1499.855),
    (22.9, 5.0, "PcS", 721.384),
    (22.9, 60.0, "PcS", 892.930),
    (22.9, 5.0, "ScP", 718.744),
    (22.9, 60.0, "ScP", 890.246),
    (300.0, 5.0, "PcP", 474.930),
    (300.0, 60.0, "PcP", 618.153),
    (300.0, 90.0, "PcP", 746.711),
    (300.0, 5.0, "ScS", 869.894),
    (300.0, 60.0, "ScS", 1135.240),
    (300.0, 90.0, "ScS", 1375.450),
    (300.0, 5.0, "PcS", 687.350),
    (300.0, 5.0, "ScP", 657.166),
]

# Geometries for which the requested phase has no arrival on the modelled
# branch, so it is omitted from the result entirely.
IAS91_OMITTED: list[tuple[float, float, Phase]] = [
    (22.9, 0.5, "P"),
    (22.9, 0.5, "S"),
    (0.0, 100.0, "P"),
    (22.9, 2.0, "P"),
    (0.0, 100.0, "PcP"),
    (0.0, 100.0, "ScS"),
    (0.0, 80.0, "PcS"),
    (0.0, 80.0, "ScP"),
    (300.0, 98.0, "PcP"),
]

# ak135's branch limits differ from iasp91's, so its omitted geometries
# are checked against the ak135 model explicitly. Short-distance P at
# 22.9 km is excluded here: within the tau-p branch's regional gap TauP
# reports a regional P arrival, while a broader 0.5-degree row already
# locks the omission.
AK135_OMITTED: list[tuple[float, float, Phase]] = [
    (22.9, 0.5, "P"),
    (22.9, 0.5, "S"),
    (0.0, 100.0, "P"),
    (0.0, 80.0, "PcS"),
    (0.0, 80.0, "ScP"),
    (0.0, 102.0, "ScS"),
    (0.0, 100.0, "PcP"),
    (300.0, 100.0, "PcP"),
]


@pytest.mark.parametrize(
    ("depth_km", "dist_deg", "phase", "reference"),
    IAS91_REFERENCE,
)
def test_reference_travel_times(
    depth_km: float, dist_deg: float, phase: Phase, reference: float
) -> None:
    result = travel_times(depth=depth_km * 1000.0, distance=dist_deg, phases=[phase])

    assert result.keys() == {phase}
    assert isinstance(result[phase], pd.Timedelta)
    assert pytest.approx(result[phase].total_seconds(), abs=0.01) == reference


@pytest.mark.parametrize(
    ("depth_km", "dist_deg", "phase"),
    IAS91_OMITTED,
)
def test_phase_without_arrival_is_omitted(
    depth_km: float, dist_deg: float, phase: Phase
) -> None:
    assert (
        travel_times(depth=depth_km * 1000.0, distance=dist_deg, phases=[phase]) == {}
    )


@pytest.mark.parametrize(
    ("depth_km", "dist_deg", "phase", "reference"),
    AK135_REFERENCE,
)
def test_ak135_reference_travel_times(
    depth_km: float, dist_deg: float, phase: Phase, reference: float
) -> None:
    result = travel_times(
        depth=depth_km * 1000.0,
        distance=dist_deg,
        phases=[phase],
        model="ak135",
    )

    assert result.keys() == {phase}
    assert isinstance(result[phase], pd.Timedelta)
    assert pytest.approx(result[phase].total_seconds(), abs=0.01) == reference


@pytest.mark.parametrize(
    ("depth_km", "dist_deg", "phase"),
    AK135_OMITTED,
)
def test_ak135_phase_without_arrival_is_omitted(
    depth_km: float, dist_deg: float, phase: Phase
) -> None:
    assert (
        travel_times(
            depth=depth_km * 1000.0, distance=dist_deg, phases=[phase], model="ak135"
        )
        == {}
    )


def test_multi_phase_ordering() -> None:
    result = travel_times(
        depth=22900.0, distance=60.0, phases=["P", "S", "PcP", "ScS", "PcS", "ScP"]
    )

    assert result.keys() == {"P", "S", "PcP", "ScS", "PcS", "ScP"}
    assert pd.Timedelta(0) < result["P"] < result["PcP"] < result["PcS"]
    assert pd.Timedelta(0) < result["P"] < result["S"]
    assert result["PcS"] < result["ScS"]
    assert result["ScP"] < result["PcS"]


def test_reflection_merges_with_turning_ray_at_cmb_grazing_distance() -> None:
    p = travel_times(depth=0.0, distance=98.0, phases=["P"])
    pcp = travel_times(depth=0.0, distance=98.0, phases=["PcP"])

    assert pytest.approx(p["P"].total_seconds(), abs=0.01) == pcp["PcP"].total_seconds()


def test_maule_anmo_geometry() -> None:
    result = travel_times(depth=22900.0, distance=77.63835494287527, phases=["P"])

    assert pytest.approx(result["P"].total_seconds(), abs=0.001) == 714.510930


def test_unknown_model_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported velocity model"):
        travel_times(
            depth=22900.0, distance=60.0, phases=["P"], model=cast(Model, "prem")
        )


def test_ak135_model_runs() -> None:
    # Plumbing check only: model resolves, both phases arrive, P before S.
    # Reference values against TauP are validated separately.
    tt = travel_times(depth=22900.0, distance=60.0, phases=["P", "S"], model="ak135")

    assert tt.keys() == {"P", "S"}
    assert all(isinstance(t, pd.Timedelta) and t > pd.Timedelta(0) for t in tt.values())
    assert tt["P"] < tt["S"]


@pytest.mark.parametrize("phase", ["PKP", "SKS", "pP", "PP"])
def test_unknown_phase_raises(phase: str) -> None:
    with pytest.raises(ValueError, match="Unsupported phase"):
        travel_times(depth=22900.0, distance=60.0, phases=[cast(Phase, phase)])


@pytest.mark.parametrize("depth", [-1000.0, 3_000_000.0])
def test_depth_out_of_range_raises(depth: float) -> None:
    with pytest.raises(ValueError, match="Source depth"):
        travel_times(depth=depth, distance=60.0, phases=["P"])


@pytest.mark.parametrize("distance", [-5.0, 200.0])
def test_distance_out_of_range_raises(distance: float) -> None:
    with pytest.raises(ValueError, match="Epicentral distance"):
        travel_times(depth=22900.0, distance=distance, phases=["P"])


def test_source_at_surface_and_60_degrees_match_reference() -> None:
    result = travel_times(depth=0.0, distance=60.0, phases=["P", "S"])

    assert pytest.approx(result["P"].total_seconds(), abs=0.01) == 608.280
    assert pytest.approx(result["S"].total_seconds(), abs=0.01) == 1102.731


def test_solver_values_are_stable() -> None:
    # Exact-value regression lock (tighter than the abs=0.01 reference
    # rows): these must not drift as the solver is tuned. The retired
    # EarthScope traveltime service returned 604.654 / 1096.553 here.
    tt = travel_times(depth=22900.0, distance=60.0, phases=["P", "S"])

    assert {phase: round(t.total_seconds(), 3) for phase, t in tt.items()} == {
        "P": 604.652,
        "S": 1096.551,
    }


def test_phase_literal_matches_dispatch_tables() -> None:
    assert set(get_args(Phase.__value__)) == _SUPPORTED_PHASES


def test_model_literal_matches_bundled_tvel_files() -> None:
    assert set(get_args(Model.__value__)) == {p.stem for p in _DATA_DIR.glob("*.tvel")}
