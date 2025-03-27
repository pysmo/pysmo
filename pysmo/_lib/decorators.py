from typing import Any
from collections.abc import Callable
from functools import wraps


def value_not_none(function: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to prevent the value in properties from being None"""

    @wraps(function)
    def decorator(*args: Any, **kwargs: Any) -> Any:
        instance, value, *_ = args
        if value is None:
            raise TypeError(
                f"{instance.__class__.__name__}.{function.__name__} may not be of None type."
            )
        return function(*args, **kwargs)

    return decorator


def add_doc(docstring: str) -> Callable:
    """Decorator to add a docstring to a function"""

    def decorator(function: Callable) -> Callable:
        function.__doc__ = docstring
        return function

    return decorator
