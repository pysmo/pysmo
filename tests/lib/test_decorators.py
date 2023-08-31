def test_add_doc() -> None:
    from pysmo.lib.decorators import add_doc

    test_string = f"""{123} test"""

    @add_doc(test_string)
    def my_func() -> None:
        pass

    assert my_func.__doc__ == test_string
