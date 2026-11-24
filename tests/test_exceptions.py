import pytest

from pysmo.classes import SAC
from pysmo.exceptions import MissingValueError


def test_is_type_and_value_error() -> None:
    assert issubclass(MissingValueError, TypeError)
    assert issubclass(MissingValueError, ValueError)


@pytest.mark.parametrize("builtin", [TypeError, ValueError])
def test_caught_by_builtin(builtin: type[Exception]) -> None:
    with pytest.raises(builtin):
        SAC().station.latitude
