from typing import Callable, TypeVar
from functools import wraps

Instance = TypeVar('Instance')
Value = TypeVar('Value')
ReturnType = TypeVar('ReturnType')


def value_not_none(function: Callable[[Instance, Value], ReturnType]) -> Callable[[Instance, Value], ReturnType]:
    """Decorator to prevent the value in properties from being None"""

    @wraps(function)
    def decorator(instance: Instance, value: Value) -> ReturnType:
        if value is None:
            raise TypeError(
                f"{instance.__class__.__name__}.{function.__name__} may not be of None type."
            )
        return function(instance, value)
    return decorator


def add_doc(docstring: str) -> Callable:
    """Decorator to add a docstring to a function"""
    def decorator(function: Callable) -> Callable:
        function.__doc__ = docstring
        return function
    return decorator
