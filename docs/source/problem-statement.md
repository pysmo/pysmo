# Problem Statement

Anyone who has taken a course on programming (in any language) will most likely first
have been taught about the different data types available. These typically consist of
simple types like integers, floats, strings, as well as the more complicated arrays,
dictionaries, etc. That is because type matters; passing a string to a program that
calculates the square root wouldn't make much sense. Python doesn't enforce any kind
of static typing (in some cases that is actually beneficial). However, being explicit
about what type of data a program (or function) requires, and what type of data are
returned also helps make it clear what exactly a piece of code does. In turn that code
becomes both more readable and less error prone.

As one moves from general-purpose programming towards more specialised problem solving
(e.g. within a particular scientific field), these data types may become more complex.
This is easy to do in Python, as any class is also an instance of a type. There is a
danger of these classes becoming too complicated, however. When that happens, using them
effectively requires intimate knowledge of the underlying code. As a result, anyone not
familiar enough with that class will not use it in the way it is intended, and instead
fall back to using it in a more general-purpose way. For example, instead of writing a
function that takes an instance of that class as argument directly, one might end up
writing code that first extracts certain parts of that object, saves those in new
variables, and then passes those variables to a function for further processing.

Seismogram data often comes in the form of a time series (the seismogram itself) together
with varying amounts of metadata (e.g. about the instrument recording, event information,
etc.). Most forms of processing only require a fraction of those data. In some cases
what would normally be considered metadata is actually what one is primarily interested
in, and it may be difficult to guarantee that these are actually present in the data
structure. Perhaps one is using the wrong version of a particular class, or an underlying
file that is read into a Python object is of the wrong format.

Pysmo attempts to mitigate these kinds of problems by adding a layer that sits between
the *generic classes* (i.e. a class one normally encounters in Python) and the functions
that use the data contained in these classes. This additional layer consists of a number
of *protocol classes* which define types that are more meaningful in a seismological
context. This way, something like an epicentre may be it's own type as opposed to just
being metadata in a larger object. Instead of writing a function that takes an all
encompassing object as argument, a pysmo user can instead write a function that takes
well defined types as arguments, all while still using those large all encompassing
objects, but without actually needing to know much about them.
