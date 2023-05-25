.. highlight:: python

.. _mypy: https://mypy.readthedocs.io/en/stable

Not so Fast!
============
Before getting our feet wet with pysmo, it is a good idea to review some
Python concepts that are important to pysmo (and good to know when using
Python in general).

Dynamic and Static Typing
-------------------------
Python is a *dynamically typed* language. This means that the *type* (float,
string, etc.) of a variable isn't set until we run code and assign a value
to it. This is convenient, but can produce errors at runtime if we are not
careful. This can be demonstrated with this simple function::

  def division(a, b):
    return a / b
  
We first call our function with the arguments 5 and 2. Thus both variables
``a=5`` and ``b=2`` are integers in this first run:

  >>> division(5, 2)
  2.5

In a second run, we set ``a="hello"`` and ``b="world"``. They are now strings,
and our code doesn't make much sense anymore...

  >>> division("hello", "world")
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "<stdin>", line 2, in division
  TypeError: unsupported operand type(s) for /: 'str' and 'str'


Evidently the function only can be used if the variables ``a`` and ``b`` are
numbers. To be clear, there is nothing wrong syntactically in this example,
but certain operations are only available to the correct types (which
is why we got a TypeError). To keep track of what types of input a function
accepts, and what kind of output to expect we can add *annotations* to the
above function::

  # Here we are making it clear that the function
  # expects two floats as input arguments, and that
  # the output is also a float.
  def division(a: float, b: float) -> float:
    return a / b

These annotations, also known as *type hints*, are not enforced (i.e. Python
will still happily try running that function with strings as arguments).
However, besides being a useful form of self-documentation, type hints become
very powerful in combination with a modern source code editor or third party
tools like `mypy`_. Both will scan code and catch type errors before it is
executed. This means we can effectively choose to write statically typed
Python code and prevent type errors from occurring.

Duck Typing
-----------
At this point one may ask why static typing is not enforced everywhere so that we
can be done with it? Well, sometimes it is more useful to consider how something
behaves, rather than what it actually is. This is often referred to as *duck typing*.
The same way that something can be considered a duck if it walks and talks like
one, any object that has all the right attributes and methods expected e.g. by a
function can also be used as input for that function. The following example defines two
classes for ducks and humans, and a function which runs error free when its argument
is duck-like (it can quack and waddle, rather than strictly being of type ``Duck``)::

  class Duck:
    # The duck class has two methods to walk and talk like a duck.
    def quack(self):
      return("quack, quack!")

    def waddle(self):
      return("waddle, waddle!")


  class Human:
    # A (silly) human can also walk and talk like a duck.
    def quack(self):
      return("quack, quack!")"

    def waddle(self):
      return("waddle, waddle!")"


  def like_a_duck(thing):
    # This function doesn't care if you are a duck or not, it merely
    # requires you to be able to talk and walk like one.
    try:
      thing.quack()
      thing.waddle()
      print("I must be a duck!")
    except AttributeError:
      print("I'm unable to walk and talk like a duck.")


  donald = Duck()  # create an instance of Duck called donald
  joe = Human()    # create an instance of Human called joe

  like_a_duck(donald)  # prints "I must be a duck!"
  like_a_duck(joe)     # also prints "I must be a duck!"

A real world example where this is applied is in the built-in ``len()`` function:

  >>> my_string = "hello world"
  >>> len(my_string)  # the len() function works with a string
  11
  >>> my_list = [1, 2, 3]
  >>> len(my_list)  # and with a list
  3
  >>> my_int = 42
  >>> len(my_int)  # but not with an integer
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
  TypeError: object of type 'int' has no len()

Behind the scenes, ``len()`` doesn't look for valid input types, but rather if the
object it is given as input possesses the ``__len__`` attribute:

  >>> hasattr(my_string,'__len__')
  True
  >>> hasattr(my_list,'__len__')
  True
  >>> hasattr(my_int,'__len__')
  False

Structural subtyping (static duck typing)
-----------------------------------------
The two strategies (duck vs static typing) may appear somewhat orthogonal. In cases
similar to the ``len()`` function they probably are, but what if we want duck typing
with a bit more control? Let's revisit the duck example from before, this time with
with a new ``Robot`` class and *structural subtyping*::

  # We import the Protocol class ...
  from typing import Protocol

  # ... and use it to define our Ducklike class. This protocol class
  # defines a structure (attributes and methods with their respective
  # types) that can be compared with structure present in any other
  # class. If those classes have a matching structure, they are
  # considered subclasses (in terms of typing) of the protocol class.
  class Ducklike(Protocol):

    def quack(self) -> str:
      # ellipses are preferred over "pass" statements here
      ...

    def waddle(self) -> str:
      ...

  class Duck:
    # We add type hints to the otherwise unchanged Duck class.
    # Because it has the same structure as the Ducklike protocol
    # class, it is implicitly considered a subclass of Ducklike.
    def quack(self) -> str:
      return("quack, quack!")

    def waddle(self) -> str:
      return("waddle, waddle!")


  class Human:
    # The Human class is also a subclass of Ducklike, even though
    # we added a new dance method.
    def quack(self) -> str:
      return("quack, quack!")

    def waddle(self) -> str:
      return("waddle, waddle!")

    def dance(self) -> str:
      return("shaking those hips!")


  class Robot:
    # An advanced robot can also walk and talk like a duck.
    def quack(self) -> bytes:
      # However, it talks in bytes instead of strings.
      # This means the Robot class is _not_ Ducklike
      return bytes("beep, quack!", "UTF-8")

    def waddle(self) -> str:
      return("waddle, waddle!")


  def like_a_duck(thing: Ducklike) -> None:
    # Unlike before, we do care about the type of the "thing"
    # input variable now. It should be of type "Ducklike",
    # which includes the subclasses of Ducklike (Duck, and
    # Human, but not Robot).
    try:
      thing.quack()
      thing.waddle()
      print("I must be a duck!")
    except AttributeError:
      print("I'm unable to walk and talk like a duck.")


  donald = Duck()
  joe = Human()
  robert = Robot()

  like_a_duck(donald)  # As before, this prints "I must be a duck!"
  like_a_duck(joe)     # Same for joe.
  like_a_duck(robert)  # Even this prints "I must be a duck!", but mypy will mark it
                       # incompatible type because Robot is not a subclass of Ducklike.

The above example illustrates how protocol classes are used, but doesn't explain why they
are useful. With regards to pysmo, there are two important lessons to be learned here:

#. The type annotations for the ``like_a_duck()`` function tell us it is written with the
   baseclass ``Ducklike`` in mind instead of a particular implementation of a duck class.
   This decoupling means we can write code using a well defined and consistent interface.
#. All attributes and methods in the protocol class need to be matched with the "real"
   classes, but not the other way around. The ``Duck`` or ``Human`` classes may well
   contain methods like fly, run, eat, sleep, etc. However, they can safely be ignored
   by ``like_a_duck()``.

Next steps
----------
* Learn more about type hinting and how to check your code for type errors using `mypy`_.
* If you aren't already, consider switching to using a code editor that checks your code
  (not just for typing errors) as you write it.
* Continue onwards to the :ref:`next chapter<installation:installing pysmo>` and install pysmo!
