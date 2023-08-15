from typing import Callable


def add_doc(docstring: str) -> Callable:
    """Add a docstring to a function"""
    def decorator(func: Callable) -> Callable:
        func.__doc__ = docstring
        return func
    return decorator
