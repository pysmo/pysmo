from typing import Callable, TypeVar, ParamSpec
from functools import wraps

T = TypeVar("T")
P = ParamSpec("P")


# HACK: Since the args are known this should work without
# ParamSpec (i.e. using only TypVar).
def value_not_none(function: Callable[P, T]) -> Callable[P, T]:
    """Decorator to prevent the value in properties from being None"""

    @wraps(function)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        instance, value = args
        if value is None:
            raise TypeError(
                f"{instance.__class__.__name__}.{function.__name__} may not be of None type."  # noqa: E501
            )
        return function(*args, **kwargs)

    return decorator


def add_doc(docstring: str) -> Callable:
    """Decorator to add a docstring to a function"""

    def decorator(function: Callable) -> Callable:
        function.__doc__ = docstring
        return function

    return decorator
