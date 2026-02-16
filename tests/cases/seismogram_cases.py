"""Common seismogram test cases for use across multiple test files.

This module provides pytest_cases case functions for creating test seismograms.
The cases can be used in any test file by using the parametrize_with_cases decorator.

Usage:
    from pytest_cases import parametrize_with_cases

    @parametrize_with_cases("seismogram", cases=".cases.seismogram_cases")
    def test_something(seismogram: Seismogram) -> None:
        # Test code here
        pass

Or if importing from the same package level:
    from pytest_cases import parametrize_with_cases

    @parametrize_with_cases("seismogram", cases="tests.cases.seismogram_cases")
    def test_something(seismogram: Seismogram) -> None:
        # Test code here
        pass
"""

from pysmo import MiniSeismogram
from pysmo.classes import SAC, SacSeismogram
from tests.conftest import TESTDATA


def case_sac_seismogram() -> SacSeismogram:
    """Provide a fresh SacSeismogram instance for testing.
    
    Returns a new SacSeismogram instance each time to ensure test isolation.
    """
    return SAC.from_file(TESTDATA["orgfile"]).seismogram


def case_mini_seismogram() -> MiniSeismogram:
    """Provide a fresh MiniSeismogram instance for testing.
    
    Returns a new MiniSeismogram instance each time to ensure test isolation.
    """
    sacseis = SAC.from_file(TESTDATA["orgfile"]).seismogram
    return MiniSeismogram(
        begin_time=sacseis.begin_time,
        delta=sacseis.delta,
        data=sacseis.data.copy(),  # Copy data to ensure independence
    )
