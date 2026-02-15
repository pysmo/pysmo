# First steps

Before starting your journey with pysmo, you should have a basic understanding
of *typing* in the Python programming language. More precisely, you should know
what [*type hinting*][typing] is, and how it is used in conjunction with modern
code editors (or other tools that check your code before it is executed).

!!! tip
    Keep in mind that not only do programming languages themselves evolve,
    but also the *tools* used for writing code. Thus you get the most benefit
    out of pysmo when used together with a modern editor/IDE such as
    [VSCode](https://code.visualstudio.com/),
    [PyCharm](https://www.jetbrains.com/pycharm/),
    [Neovim](https://neovim.io), etc.

## Dynamic and static typing

Python is a *dynamically* typed language. This means that the type
([`float`][float], [`str`][str], etc.) of a variable isn't set until you run
code and assign a value to it. This is convenient, but can produce errors at
runtime if you are not careful. This can be demonstrated with this simple
function:

```py title="division.py"
--8<-- "docs/snippets/division.py"
```

We load this function into an interactive Python session and call it with
the arguments `#!py 5` and `#!py 2`. Thus both variables `#!py a=5` and
`#!py b=2` are numbers and we get the expected result:

<!-- invisible-code-block: python 
```python
>>> from docs.snippets.division import division
```
-->

<!-- skip: next -->

```python
$ python -i division.py
>>> division(5, 2)
2.5 # (1)!
>>>
```

1. :material-lightbulb: In Python, dividing two integers always creates a
  float!

In a second run they are set to `#!py a="hello"` and `#!py b="world"`. They
are now strings, and the code doesn't make much sense anymore...

```python
>>> division("hello", "world")
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<stdin>", line 2, in division
TypeError: unsupported operand type(s) for /: 'str' and 'str'
>>>
```

Evidently the function can only be used if the variables `#!py a` and `#!py b`
are numbers. To be clear, there is nothing wrong *syntactically* in this
example, but certain operations are only available to the correct types (which
is why a [`TypeError`][TypeError] was raised at runtime). In order to detect
these kinds of issues *before* running a program, Python allows adding type
annotations to variables. This helps keep track of what types of input a
function accepts, and what kind of output to expect:

```py title="division_annotated.py"
--8<-- "docs/snippets/division_annotated.py"
```

1. Besides specifying that `#!py a` and `#!py b` are expected to be floats,
    we are also making it clear that the object returned by the
    function is also a float. This is important if the output of
    the `#!py division` function itself is used elsewhere.

These annotations, also known as *type hints*, are not enforced (i.e. Python will
still happily try running that function with strings as arguments). However,
besides being a useful form of self-documentation, type hints become very
powerful in combination with a modern source code editor, or third party tools
like [mypy](https://mypy.readthedocs.io). Both will scan code and catch type
errors in your code before it is executed, making it sort of "quasi statically
typed" (1).
{ .annotate }

1. :material-lightbulb: because you can run your code even with type errors!

## Duck typing

At this point one may ask why static typing is not enforced everywhere. Well,
sometimes it is more useful to consider how something behaves, rather than what
it actually is. This is often referred to as *duck typing*. The same way that
something can be considered a duck if it walks and talks like one, any object
that has all the right attributes and methods expected e.g. by a function, can
also be used as input for that function. The following example defines two
classes for ducks and humans, and a function which runs error free when its
argument is duck-like (it can quack and waddle, rather than strictly being of
type `Duck`):

```py title="duck.py"
--8<-- "docs/snippets/duck.py"
```

1. The `Duck` class has two methods: `quack` and `waddle`.

2. A human can walk (`waddle`) and talk (`quack`) like a duck.

3. This function, designed to answer the question of whether or not
    a `thing` is a duck, actually doesn't really care if the `thing` is a
    indeed a `duck` (or not). It merely requires the `thing` to be able to
    talk and walk like one. It will determine that any `thing` that is
    able to `quack` and `waddle` is a `duck`.

We then use this class in an interactive session, where the `is_a_duck` function
tells us that `donald` (correctly) and `joe` (incorrectly) are both ducks:

<!-- invisible-code-block: python 
```python
>>> from docs.snippets.duck import Duck, Human
```
-->

<!-- skip: next -->

```python
$ python -i duck.py
>>> donald = Duck()  # (1)!
>>> joe = Human()  # (2)!
>>> is_a_duck(donald)
I must be a duck!
>>> is_a_duck(joe)
I must be a duck!
>>>
```

1. Create an instance of `Duck` called `donald`.
2. Create an instance of `Human` called `joe`.

The reason for this, is simply because the `is_a_duck` function doesn't check at
all what it is given as input; as long as the `thing` object has the methods
`quack` and `waddle` it will happily tell us something is a `duck`. Note that
in some instances this is actually desired behaviour.

??? example "Duck typing in the wild."

    A real world example where duck typing is used in Python, is in the
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
    3.  :fontawesome-solid-xmark: But not with an integer.

    Behind the scenes, [`len()`][len] doesn't look for valid input
    types, but rather if the object it is given as input possesses the
    [`__len__()`][object.__len__] attribute:

    ```python
    >>> hasattr(my_string,'__len__')
    True
    >>> hasattr(my_list,'__len__')
    True
    >>> hasattr(my_int,'__len__')
    False
    >>>
    ```

Note that we haven't annotated `#!py is_a_duck()` with a type signature, making
it quite fragile. If we were to change `Duck` or `Human` in ways that make them
incompatible with the function we wouldn't find out until runtime. To fix this,
we could annotate `#!py is_a_duck()` like this:

```py
def is_a_duck(thing: Duck | Human) -> None: ...
```

`#!py is_a_duck()` now accepts only objects of type `Duck` or `Human`. This
is now much safer to use, but it is also strongly coupled to both `Duck` and
`Human`. If we were to change either of those classes, we might have to also
change the function (or even the other class!). If we wanted to use a third
class with this function some time in the future, we might find ourselves
similarly forced to edit code all over the place to make things work. Using
type hints like this to define a function that works with multiple different
input types quickly reaches its limits. Fortunately, Python has a solution to
this problem: [`Protocol`][typing.Protocol] classes.

## Structural subtyping (static duck typing)

The two strategies (duck vs static typing) may appear somewhat orthogonal. In
cases similar to the [`#!py len()`][len] function they probably are, but what
if we want duck typing with a bit more control? This is indeed possible with a
strategy called
[structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html).
Revisiting the duck example from before, this time with a new `Robot`
class and structural subtyping:

```py title="duck_protocol.py"
--8<-- "docs/snippets/duck_protocol.py"
```

1. We import the [`Protocol`][typing.Protocol] class ...
2. ... and use it to define our `Ducklike` class. This protocol class defines a
    structure (attributes and methods with their respective types) that can be
    compared with the structure present in any other class. If those classes have a
    matching structure, they are considered subclasses (in terms of typing) of
    the protocol class.
3. :bulb: Ellipses (`...`) are preferred over `pass` statements here.
4. We add type hints to the otherwise unchanged Duck class. Because it has the
    same structure as the `Ducklike` protocol class, it is implicitly considered
    a subclass of `Ducklike`.
5. The Human class is also a subclass of `Ducklike`, even though we added a new
    dance method.
6. An advanced robot can also walk and talk like a duck. However, it talks in
    bytes instead of strings. This means the `Robot` class is *not* `Ducklike`
7. Unlike before, we only add annotations for one class
    (the [`Protocol`][typing.Protocol] class) to the function. It is now *not*
    coupled to any specific classes anymore. All we are saying is that the
    function works with things that are `Ducklike` (i.e. the subclasses of
    `Ducklike` - `Duck`, and `Human`, but *not* `Robot`).

Loading this new version into an interactive Python session we get the
following:

<!-- invisible-code-block: python 
```python
>>> from docs.snippets.duck_protocol import Duck, Human, Robot
```
-->

<!-- skip: next -->

```python
$ python -i duck_protocol.py
>>> donald = Duck()
>>> joe = Human()
>>> robert = Robot()
>>> like_a_duck(donald)
I must be a duck!
>>> like_a_duck(joe)
I must be a duck!  # (1)!
>>> like_a_duck(robert)
I must be a duck!  # (2)!
>>>
```

1. As before, `donald` and `joe` appear to be `ducks`.
2. Even this prints "I must be a duck!", but mypy or your IDE will
    mark it as incompatible.

The above example illustrates how [`Protocol`][typing.Protocol] classes are
used, but doesn't explain why they are useful. With regards to pysmo, there are
two important lessons to be learned here:

1. The type annotations for the `#!py like_a_duck()` function tell us it is
   written with the base class `Ducklike` in mind instead of a particular
   implementation of a `duck` class. This decoupling means we can write code
   using a well defined and consistent interface.
2. All attributes and methods in the [`Protocol`][typing.Protocol] class need
   to be matched with the "real" classes, but not the other way around. The
   `Duck` or `Human` classes may well contain methods like `fly`, `run`, `eat`,
   `sleep`, etc. However, they can safely be ignored by `#!py like_a_duck()`.

In isolation the above two points may not appear that significant, but when we
put them together the implications are quite substantial. The goal when writing
code should always be to make it easy to understand and as reusable as possible,
after all. [Protocol][typing.Protocol] classes help with exactly that. They are
almost always going to be far less complex than a generic class(1). As such they
allow breaking up a problem into smaller pieces, and write e.g. a function that
works with a certain protocol rather than one particular class. The protocols
define an interface a function can work with. It's as if a contract exists
between a class and a function, whereby the class guarantees that the part they
have a contract for is never going to change, regardless of what might happen
elsewhere in the class. In pysmo, these contracts are the *types* we will
discuss in greater detail later on.
{ .annotate }

1. A generic class is a *proper* class, which holds data, has methods and
   attributes etc (unlike a [`Protocol`][typing.Protocol] class, which only
   contains the structure of a class).

## Next steps

* Learn more about type hinting and how to check your code for type errors using
  [mypy](https://mypy.readthedocs.io).
* If you aren't already, consider switching to using a code editor that checks
  your code (not just for typing errors) as you write it.
* Continue onwards to the [next chapter](installation.md) and install pysmo!
