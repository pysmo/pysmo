---
tags:
  - First steps
---
# First steps

Understanding why pysmo is structured the way it is requires a brief look at
how Python thinks about types. This section covers [*type hints*][typing],
duck typing, and structural subtyping — the three ideas that together make
protocol-based design possible. The concepts are not specific to pysmo, and are worth understanding in their
own right. Those already comfortable with typing in Python can skip ahead to
the [next section](installation.md).

!!! tip
    Python's type system only pays off in full when your editor understands it
    too. A modern editor or IDE such as [VSCode](https://code.visualstudio.com/),
    [PyCharm](https://www.jetbrains.com/pycharm/), or
    [Neovim](https://neovim.io) will flag type errors as you write, turning
    hints into immediate feedback.

## Dynamic and static typing

Python is a *dynamically* typed language: the type ([`float`][float],
[`str`][str], etc.) of a variable is not fixed until a value is assigned at
runtime. This is convenient, but means type errors only surface when the
offending code is actually executed. Consider this simple function:

```python
>>> def division(a,b):
...     return a/b
```

With numeric arguments it works as expected(1):
{ .annotate }

1. :material-lightbulb: In Python, dividing two integers always creates a
  float!

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

There is nothing wrong *syntactically* — Python accepts the call without
complaint. The error only appears at runtime, when the `/` operator finds
itself applied to strings. To catch these issues earlier, Python allows adding
type annotations:

```py title="division_annotated.py"
--8<-- "docs/snippets/division_annotated.py"
```

1. The return type annotation matters too — if the output of `division` is
    used elsewhere, downstream code knows what type to expect.

Type hints are not enforced — Python will still attempt to run annotated code
with the wrong argument types. Their value is elsewhere: as documentation, and
as input to tools like [mypy](https://mypy.readthedocs.io) or a type-aware
editor that can flag errors before the code runs (1).
{ .annotate }

1. :material-lightbulb: typically with squiggly red underlines and error
   messages on hover.

## Duck typing

Type hints describe what something *is*, but sometimes it is more useful to
consider what something *does*. This is *duck typing*: if an object has the
right attributes and methods, it can be used regardless of its actual type —
the same way something can be considered a duck if it walks and quacks like
one. The following example defines two classes and a function that accepts
either, not by checking the type, but by checking the behaviour:

```py title="snippets/duck.py"
--8<-- "docs/snippets/duck.py"
```

1. Two methods: `quack` and `waddle`.
2. A human can also quack and waddle.
3. Accepts anything that can `quack` and `waddle` — not just `Duck` instances.

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

`is_a_duck` never checks the type of its argument — only whether it has
`quack` and `waddle`. Sometimes that is exactly what you want.

??? example "Duck typing in the wild."
    A real-world example where duck typing is used in Python, is in the
    built-in [`#!py len()`][len] function:

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

    1.  :material-check: The [`#!py len()`][len] function works with a string,
        where it returns the number of characters in the string ...
    2.  :material-check: ... and with a list, where it returns the number
        of items in the list.
    3.  :material-close: But not with an integer.

    Behind the scenes, [`len()`][len] doesn't look for valid input
    types, but rather if the object it is given as input possesses the
    [`__len__()`][object.__len__] attribute:

    ```python
    >>> hasattr(my_string, '__len__')
    True
    >>> hasattr(my_list, '__len__')
    True
    >>> hasattr(my_int, '__len__')
    False
    >>>
    ```

Without a type signature, `#!py is_a_duck()` is fragile — changes to `Duck`
or `Human` that break the function would only surface at runtime. Adding one
helps:

```py
def is_a_duck(thing: Duck | Human) -> None: ...
```

Safer, but now tightly coupled to both `Duck` and `Human`. Adding a third
compatible class means updating the function, and changes to either class
become potential edits everywhere it is used. Type hints used this way scale
poorly. [`Protocol`][typing.Protocol] classes offer a better approach.

## Structural subtyping (static duck typing)

A [`Protocol`][typing.Protocol] class defines a structure — the attributes and
methods a conforming class must provide — without requiring inheritance. Any
class that matches is implicitly a subtype, checked statically by mypy or your
editor rather than at runtime. This is
[structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html):
duck typing, but with static checking. Revisiting the duck example with an
additional `Robot` class:

```py title="snippets/duck_protocol.py"
--8<-- "docs/snippets/duck_protocol.py"
```

1. Defines the `Ducklike` protocol — any class with matching `quack` and
    `waddle` signatures satisfies it, no inheritance required.
2. :material-lightbulb: Ellipses (`...`) are preferred over `pass` here.
3. Implicitly `Ducklike` — the structure matches, so no explicit declaration
    is needed.
4. Also `Ducklike` despite having an extra `dance` method — the protocol only
    requires what it defines.
5. `Robot.quack()` returns `bytes`, not `str` — close, but not `Ducklike`.
6. Typed against the protocol rather than specific classes — `Robot` will be
    flagged by mypy or your editor, while `Duck` and `Human` pass.

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

Python does not enforce type hints at runtime, so all three calls succeed.
The difference only shows up statically — `Robot.quack()` returns `bytes`
instead of `str`, which does not satisfy the `Ducklike` signature. A type
checker will flag this before the code runs:

```python
>>> from snippets.duck_protocol import Ducklike
>>> from typing import get_type_hints
>>>
>>> get_type_hints(Ducklike.quack) == get_type_hints(robert.quack)
False
>>> get_type_hints(Ducklike.quack) == get_type_hints(donald.quack)
True
>>> get_type_hints(Ducklike.quack) == get_type_hints(joe.quack)
True
>>>
```

Two properties of [`Protocol`][typing.Protocol] classes matter here:

1. A function typed against a protocol is decoupled from any particular
   implementation — it works with any class that satisfies the structure,
   including ones written long after the function was.
2. Conforming classes must match all protocol attributes, but may have others.
   `like_a_duck()` works with `Duck` and `Human` despite methods it never
   touches.

[`Protocol`][typing.Protocol] classes are typically much simpler than the
classes they describe(1) — they contain only what a function needs to know.
Think of them as a contract: a class that satisfies a protocol guarantees that
interface regardless of what else it does, and functions written against it are
free to ignore everything else. In pysmo, these contracts are the *types* we
will explore in the next section.
{ .annotate }

1. Unlike a regular class, a [`Protocol`][typing.Protocol] class contains only
   structural information — no data, no implementation.

## Next steps

* Learn more about type hinting and static analysis with
  [mypy](https://mypy.readthedocs.io).
* If you are not already using an editor that checks your code as you write,
  now is a good time to switch.
* Continue to the [next chapter](installation.md) and install pysmo.
