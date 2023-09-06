# Not so Fast!

Pysmo relies on certain more recent concepts of the Python programming language. These
concepts also dictate how pysmo is used, and it is important to understand them before
properly getting started. Fortunately, most of this is actually pretty mainstream these
days, so there is a good chance you already know a lot of what is discussed here. If not,
we urge you to really try and understand what is written in this section. We promise it
will come in handy in the future even if you decide pysmo is not for you!


!!! tip "Important"
    Keep in mind that not only do programming languages themselves evolve,
    but also the *tools* used for writing code. This naturally effects the
    code we write too. For example, most code editors support auto-completion,
    and because of that we are more likely to use longer (and more descriptive)
    variable names instead of confusing single letter ones.

    However, the ways in which an editor can assist us with writing code go
    way beyond just auto-completing variable names. Modern code editors are
    able to understand how different parts of our code are connected (even
    across multiple files), and thus able to warn us about things like: "hey,
    you're trying to perform a string operation on a float!". These features
    don't come completely for free, however. Our code editor needs to be given
    a few hints to do this, and that is a big part of what this section is
    about.


## Dynamic and Static Typing

Python is a *dynamically* typed language. This means that the type (float, string, etc.)
of a variable isn't set until you run code and assign a value to it. This is convenient,
but can produce errors at runtime if you are not careful. This can be demonstrated with
this simple function:

```python title="division.py"
def division(a, b):
  return a / b
```

We load load this function into an interactive Python session and call it with the
arguments '5' and '2'. Thus both variables `a=5` and `b=2` are numbers and we get the
expected result

```python
$ python -i division.py
>>> division(5, 2)
2.5 # (1)!
>>>
```

1.  :material-lightbulb: In Python, dividing two integers always creates a float!

In a second run, they are set to `a="hello"` and `b="world"`. They
are now strings, and the code doesn't make much sense anymore...

```python
>>> division("hello", "world")
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<stdin>", line 2, in division
TypeError: unsupported operand type(s) for /: 'str' and 'str'
>>>
```


Evidently the function only can be used if the variables `a` and `b` are numbers. To be
clear, there is nothing wrong syntactically in this example, but certain operations are
only available to the correct types (which is why a [TypeError][] was raised). To keep track
of what types of input a function accepts, and what kind of output to expect,
*annotations* can be added to the above function:

```python title="division_annotated.py"
def division(a: float, b: float) -> float: # (1)!
  return a / b
```

1.  Besides specifying that `a` and `b` are expected to be floats,
    we are also making it clear that the object returned by the
    function is also a float. This is important if the output of
    the `division` function itself is used elsewhere.

These annotations, also known as *type hints*, are not enforced (i.e. Python will still
happily try running that function with strings as arguments). However, besides being a
useful form of self-documentation, type hints become very powerful in combination with a
modern source code editor or third party tools like [mypy](https://mypy.readthedocs.io).
Both will scan code and catch type errors before it is executed. This means you can
effectively choose to write statically typed Python code and prevent type errors from
occurring at runtime.

## Duck Typing

At this point one may ask why static typing is not enforced everywhere so that we can be
done with it? Well, sometimes it is more useful to consider how something behaves, rather
than what it actually is. This is often referred to as *duck typing*. The same way that
something can be considered a duck if it walks and talks like one, any object that has
all the right attributes and methods expected e.g. by a function, can also be used as
input for that function. The following example defines two classes for ducks and humans,
and a function which runs error free when its argument is duck-like (it can quack and
waddle, rather than strictly being of type `Duck`):


```py title="duck.py"
--8<-- "docs/snippets/duck.py"
```

1.  The duck class has two methods: `quack`and `waddle`.

2.  A human can walk (waddle) and talk (quack) like a duck.

3.  This function, designed to answer the question of whether or not
    a `thing` is a duck, actually doesn't really care if the thing is a
    indeed a duck (or not). It merely requires the thing to be able to
    talk and walk like one. It will determine that any `thing` that is
    able to quack and waddle is a duck.


We then use this class in an interactive session, where the `is_a_duck` function tells us
that `donald` (correctly) and `joe` (incorrectly) are both ducks:

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

1.  Create an instance of Duck called donald.
2.  Create an instance of Human called joe.

The reason for this, is simply because the `is_a_duck` function doesn't check at all
what it is given as input; as long as the `thing` object has the methods `quack` and
`waddle` it will happily tell us something is a duck. Note that in some instances this is
actually desired behavior.

??? example "Duck typing in the wild."

    A real world example where duck typing is used in Python, is in the
    built-in [`len()`][len] function:

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
    ```

    1.  :material-check: The len() function works with a string, where
        it returns the number of characters in the string ...
    2.  :material-check: ... and with a list, where it ruturns the number
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
    ```

## Structural subtyping (static duck typing)
The two strategies (duck vs static typing) may appear somewhat orthogonal. In cases
similar to the [`len()`][len] function they probably are, but what if we want
duck typing with a bit more control? This is indeed possible with a strategy called
[structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html). Revisiting
the duck example from before, this time with with a new `Robot` class and structural
subtyping:

```py title="duck_protocol.py"
--8<-- "docs/snippets/duck_protocol.py"
```

1.  We import the Protocol class ...
2.  ... and use it to define our `Ducklike` class. This protocol class defines a
    structure (attributes and methods with their respective types) that can be
    compared with structure present in any other class. If those classes have a
    matching structure, they are considered subclasses (in terms of typing) of
    the protocol class.
3.  Ellipses are preferred over "pass" statements here.
4.  We add type hints to the otherwise unchanged Duck class. Because it has the
    same structure as the `Ducklike` protocol class, it is implicitly considered
    a subclass of `Ducklike`.
5.  The Human class is also a subclass of `Ducklike`, even though we added a new
    dance method.
6.  An advanced robot can also walk and talk like a duck. However, it talks in
    bytes instead of strings. This means the `Robot` class is _not_ `Ducklike`
7.  Unlike before, we _do_ care about the type of the "thing" input variable now
    (because we are using type hints). It should be of type `Ducklike`, which
    includes the subclasses of `Ducklike` (`Duck`, and `Human`, but *not* `Robot`).


Loading this new version into an interactive python session we get the following:

```python
$ python -i duck_protocol.py
>>> donald = Duck()
>>> joe = Human()
>>> robert = Robot()
>>> like_a_duck(donald)
I must be a duck!
like_a_duck(joe)
I must be a duck!  # (1)!
like_a_duck(robert)
I must be a duck!  # (2)!
>>>
```

1.  As before, donald and joe appear to be ducks.
2.  Even this prints "I must be a duck!", but mypy or your IDE will
    mark it as incompatible.

The above example illustrates how protocol classes are used, but doesn't explain why they
are useful. With regards to pysmo, there are two important lessons to be learned here:

1.  The type annotations for the `like_a_duck()` function tell us it is written with the
    baseclass `Ducklike` in mind instead of a particular implementation of a duck class.
    This decoupling means we can write code using a well defined and consistent interface.
2.  All attributes and methods in the protocol class need to be matched with the "real"
    classes, but not the other way around. The `Duck` or `Human` classes may well contain
    methods like fly, run, eat, sleep, etc. However, they can safely be ignored by
    `like_a_duck()`.

In isolation the above two points may not appear that significant, but when we put them
together the implications are quite substantial. The goal when writing code should always
be to make it easy to understand and as reusable as possible, after all.
[Protocol][typing.Protocol] classes help with exactly that. They are almost always going
to be far less complex than a generic class(1). As such they allow breaking up a problem
into smaller pieces, and write e.g. a function that works with a certain protocol rather
than one particular class. The protocols define an interface a function can work with.
It's as if a contract exists between a class and a function, whereby the class guarantees
that the part they have a contract for is never going to change, regardless of what might
happen elsewhere in the class. In pysmo, these contracts are the *types* we will discuss
in greater detail later on.
{ .annotate }

1.  A generic class is a *proper* class, which holds data, has methods and attributes
    etc (unlike a [protocol][typing.Protocol] class, which only contains the structure
    of a class).

!!! note
    It is also much easier to design a new class to work with existing functions
    using protocols (provided the functions were also written with protocols in
    mind, of course). Consider for example a problem that typically would involve
    storing data in files of a particular format, and using a Python class to
    access and manipulate data in these files. The file format, Python class, and
    all the Python scripts would likely be strongly coupled to each other in such
    a scenario. Given how much data are produced these days, it is conceivable that
    our hypothetical project might also grow to a point where storing data in
    individual files is no longer feasible, and instead something like a database
    must be used. A class to access a database is likely wildly different to one
    designed for accessing a particular file format. Thus it would be quite a big
    task to create a new class that works with the database, while also being
    compatible with the existing code that up until now was always using data
    from files. This would be trivial had protocols been used from the beginning.
    The types defined by protocols are always going to be simpler than types
    defined by generic classes, as they strip away the intrinsic complexities
    stemming from things like file or database access. In short, because the
    existing functions would not have to concern themselves with things like
    file access, the newly designed "database class" would also not have to.


## Next steps

* Learn more about type hinting and how to check your code for type errors using
  [mypy](https://mypy.readthedocs.io).
* If you aren't already, consider switching to using a code editor that checks your code
  (not just for typing errors) as you write it.
* Continue onwards to the [next chapter](installation.md)
  and install pysmo!
