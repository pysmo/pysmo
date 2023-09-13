from dataclasses import dataclass

import pytest


def test_value_not_none() -> None:
    from pysmo.lib.decorators import value_not_none

    @dataclass
    class A:
        _foo: float = 0

        @property
        def foo(self) -> float:
            return self._foo

        @foo.setter
        @value_not_none
        def foo(self, value: float) -> None:
            self._foo = value

    a = A()
    assert a.foo == 0
    a.foo = 2.2
    assert a.foo == 2.2
    with pytest.raises(TypeError):
        a.foo = None  # type: ignore


def test_add_doc() -> None:
    from pysmo.lib.decorators import add_doc

    test_string = f"""{123} test"""

    @add_doc(test_string)
    def my_func() -> None:
        pass

    assert my_func.__doc__ == test_string
