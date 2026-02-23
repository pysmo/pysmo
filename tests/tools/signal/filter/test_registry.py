from typing import get_args
from pysmo.tools.signal import filter
from pysmo.tools.signal._filter._filter import FilterName
from pysmo.tools.signal._filter._registry import _FILTER_REGISTRY


def test_filter_registry_matches_literal() -> None:
    """
    Ensure that the FilterName Literal in _filter.py matches the functions
    registered with @register_filter.
    """
    # Ensure all filters are registered by the time we check
    assert filter is not None

    # FilterName is a TypeAliasType in Python 3.12+
    if hasattr(FilterName, "__value__"):
        literal_values = set(get_args(FilterName.__value__))
    else:
        literal_values = set(get_args(FilterName))

    registry_values = set(_FILTER_REGISTRY.keys())

    assert literal_values == registry_values, (
        f"Literal values {literal_values} do not match "
        f"registry values {registry_values}. "
        "Did you forget to update FilterName in _filter.py "
        "or forget to decorate a new filter with @register_filter?"
    )
