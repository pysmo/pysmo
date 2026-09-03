---
tags:
  - First steps
---

# First steps

Understanding why pysmo is structured the way it is requires a brief look at how
Python thinks about types. This section covers [*type hints*][typing], duck
typing, and structural subtyping: the three ideas that together make
protocol-based design possible. The concepts are not specific to pysmo and are
worth understanding in their own right. Those already comfortable with typing in
Python can skip ahead to [installation](installation.md).

!!! tip "Use a modern editor"

    Python's type system only pays off in full when the editor understands it too. A
    modern editor or IDE such as [VSCode](https://code.visualstudio.com/),
    [PyCharm](https://www.jetbrains.com/pycharm/), or [Neovim](https://neovim.io)
    flags type errors as the code is written, turning hints into immediate feedback.

## Type hints

Python is a *dynamically* typed language: the type ([`float`][], [`str`][],
etc.) of a variable is not fixed until a value is assigned at runtime. This is
convenient, but it means type errors only surface when the offending code runs.
Consider this simple function:

```python
>>> def division(a,b):
...     return a/b
```

With numeric arguments it works as expected(1):
{ .annotate }

1. :material-lightbulb: In Python, dividing two integers always creates a float.

```python
>>> division(5, 2)
2.5
>>>
```

Passing strings instead:

```python
>>> division("hello", "world")
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<stdin>", line 2, in division
TypeError: unsupported operand type(s) for /: 'str' and 'str'
>>>
```

There is nothing wrong *syntactically*. Python accepts the call without
complaint. The error only appears at runtime, when the `/` operator is applied
to strings. To catch these issues earlier, Python allows adding type
annotations:

```py title="division_annotated.py"
--8<-- "docs/snippets/division_annotated.py"
```

1. The return type annotation matters too. If the output of `division` is used
    elsewhere, downstream code knows what type to expect.

Running [mypy](https://mypy.readthedocs.io) over the file reports the bad call,
without executing anything:

```text
division_annotated.py:5: error: Argument 1 to "division" has incompatible type "str"; expected "float"  [arg-type]
division_annotated.py:5: error: Argument 2 to "division" has incompatible type "str"; expected "float"  [arg-type]
Found 2 errors in 1 file (checked 1 source file)
```

A type-aware editor shows the same errors inline, as the code is written (1).
{ .annotate }

1. :material-lightbulb: typically with squiggly red underlines and error
    messages on hover.

The hints are not enforced at runtime. Python still runs `division("a", "b")`
and raises the same [`TypeError`][] as before. Their job is to surface the
mistake earlier: in the editor, in review, in CI.

## Duck typing

The hints above name built-in types like `float` and `str`. Most code also
passes around objects, often instances of purpose-built classes. A function can
name such a class in its signature, for example `thing: Duck`. That works, but
it is often stricter than needed. If the function only calls `thing.quack()`,
any object with a `quack()` method would serve.

Focusing on what an object can *do*, rather than what it *is*, is *duck typing*.
The name comes from calling something a duck when it walks and quacks like one.
The following example defines two classes and a function that accepts either. It
checks the behaviour, not the type:

```py title="snippets/duck.py"
--8<-- "docs/snippets/duck.py"
```

1. Two methods: `quack` and `waddle`.
2. A human can also quack and waddle.
3. Accepts anything that can `quack` and `waddle`, not just `Duck` instances.

```python
>>> from snippets.duck import Duck, Human, is_a_duck
>>> donald = Duck()
>>> joe = Human()
>>> is_a_duck(donald)
I must be a duck!
>>> is_a_duck(joe)
I must be a duck!
>>>
```

`is_a_duck` never checks the type of its argument, only whether it has `quack`
and `waddle`. Sometimes that is exactly what is needed.

??? example "Duck typing in the wild"

    A real-world example of duck typing in Python is the built-in
    [`#!py len()`][len] function:

    ```python
    >>> my_string = "hello world"
    >>> len(my_string) # the len() function works with a string (1)!
    11
    >>> my_list = [1, 2, 3]
    >>> len(my_list) # and with a list (2)!
    3
    >>> my_int = 42
    >>> len(my_int) # but not with an integer (3)!
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: object of type 'int' has no len()
    >>>
    ```

    1. :material-check: The `#!py len()` function works with a string, where it
        returns the number of characters in the string ...
    2. :material-check: ... and with a list, where it returns the number of items in
        the list.
    3. :material-close: But not with an integer.

    Behind the scenes, `len()` doesn't check the input type. It checks whether the
    object has the [`__len__()`][object.__len__] method that `len()` looks for:

    ```python
    >>> hasattr(my_string, '__len__')
    True
    >>> hasattr(my_list, '__len__')
    True
    >>> hasattr(my_int, '__len__')
    False
    >>>
    ```

Without a type signature, `#!py is_a_duck()` is fragile. Changes to `Duck` or
`Human` that break the function would only surface at runtime. Adding one helps:

```py
def is_a_duck(thing: Duck | Human) -> None: ...
```

This is safer, but now tightly coupled to both `Duck` and `Human`. Adding a
third compatible class means updating the function. Changes to either class
become potential edits everywhere it is used. Type hints used this way scale
poorly. [`Protocol`][typing.Protocol] classes offer a better approach.

## Structural subtyping (static duck typing)

A `Protocol` class defines a structure: the attributes and methods a conforming
class must provide. No inheritance is required. Any class that matches is
implicitly a subtype. The match is checked statically, by mypy or the editor,
rather than at runtime. This is
[structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html):
duck typing with static checking. Revisiting the duck example with an additional
`Robot` class:

```py title="snippets/duck_protocol.py"
--8<-- "docs/snippets/duck_protocol.py"
```

1. Defines the `Ducklike` protocol: any class with matching `quack` and `waddle`
    signatures satisfies it, no inheritance required.
2. :material-lightbulb: Ellipses (`...`) are preferred over `pass` here.
3. Implicitly `Ducklike`: the structure matches, so no explicit declaration is
    needed.
4. Also `Ducklike` despite having an extra `dance` method; the protocol only
    requires what it defines.
5. `Robot.quack()` returns `bytes`, not `str`. Close, but not `Ducklike`.
6. Typed against the protocol rather than specific classes. `Robot` will be
    flagged by mypy or the editor, while `Duck` and `Human` pass.

The runtime behaviour is the same as before:

```python
>>> from snippets.duck_protocol import Duck, Human, Robot, is_a_duck
>>>
>>> donald = Duck()
>>> joe = Human()
>>> robert = Robot()
>>> is_a_duck(donald)
I must be a duck!
>>> is_a_duck(joe)
I must be a duck!
>>> is_a_duck(robert)
I must be a duck!
>>>
```

Python does not enforce type hints at runtime, so all three calls succeed. The
difference only shows up statically. `Robot.quack()` returns [`bytes`][] instead
of `str`, which does not satisfy the `Ducklike` signature, so mypy or the editor
flags the `is_a_duck(robert)` call before the code runs.

Two properties of `Protocol` classes matter here:

1. A function typed against a protocol is decoupled from any particular
    implementation. It works with any class that satisfies the structure,
    including ones written long afterwards.
2. Conforming classes must match all protocol attributes, but may have others.
    `is_a_duck()` works with `Duck` and `Human` despite methods it never
    touches.

`Protocol` classes are typically much simpler than the classes they describe(1).
They contain only what a function needs to know. Think of them as a contract. A
class that satisfies a protocol guarantees that interface regardless of what
else it does. Functions written against it are free to ignore everything else.
In pysmo, these contracts are the *types*, covered in depth in the
[Usage](../usage/index.md) chapter.
{ .annotate }

1. Unlike a regular class, a `Protocol` class contains only structural
    information: no data, no implementation.

## Next steps

- Learn more about type hinting and static analysis with
    [mypy](https://mypy.readthedocs.io).
- Switch to an editor that checks code as it is written, if not already using
    one.
- Continue to the [next chapter](installation.md) and install pysmo.
