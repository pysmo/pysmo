# Types

This chapter goes into detail about the *types* provided by pysmo. They are at the core
of how pysmo works, and it is therefore worth briefly reviewing the relationship between
types and classes in Python. This relationship can be explained using the built-in float
type:

```python
>>> # We first assign a float to the variable a
>>> a = 1.2
>>>
>>> # Then we verify it is indeed a float using the "type" command
>>> type(a)
<class 'float'>
>>>
>>> # The type of the float class is...
>>> type(float)
<class 'type'>
```

Remember, in Python everything is an object. So in the above snippet we created an object
called `a`{l=python} of the [`float`{l=python}](inv:python#float) class (objects are
instances of a class). Where it gets interesting, is when we query what type our variable
`a`{l=python} is using the [`type`{l=python}](inv:python:py#type) command; instead of
returning simply "float", the Python interpreter tells us the type of `a`{l=python} is
`<class 'float'>`. In other words, the [`float`{l=python}](inv:python#float)
class is itself a type (which we verify in the last line). Simply put then, every time we
define a class in Python, we also define a type.


## Protocol Classes

[Protocol classes](inv:mypy#protocols) were introduced in Python 3.8, and are discussed
in detail in [PEP 544](https://peps.python.org/pep-0544/). In this section, we explain
how (and why) they are used in pysmo.

Especially when dealing with data that exist in the physical world, we are of the
opinion that a type should not just be an arbitrary and abstract thing. Therefore
there ought to be meaningful relationship between a class name, and the information
contained within that class. In the above example we put a floating point number in a
[`float`{l=python}](inv:python#float) object. It is pretty much self-explanatory what the
float class is for, and it seems unlikely the definition of the float class is ever going
to drastically change. If we were to write a function that requires its input to be a
floating point number, we can simply make it a requirement that any input is of type
[`float`{l=python}](inv:python#float) and we never run into trouble.

We reckon a similarly unambiguous definition is possible for a lot of types of data
routinely encountered by seismologists. For example, an epicenter will always consist
precisely (and only) of a set of coordinates, a hypocentre of an epicenter and a depth,
and so on. In pysmo we formulise this by using protocol classes to define these
seismology-specific types.


### How they work

Protocol classes serve as an interface between objects containing data, and functions
using data. This is not unlike a web browser "speaking" html to communicate with a web
server to request and then display data on screen. We use a hypothetical example to
explore what this looks like, what some of the benefits are, and also perhaps some
peculiarities one might have to be wary of.

Our hypothetical data class [^dataclass] contains only a seismogram, station and event
data. We consider using an instance of this class directly to be the *traditional*
approach, while using it via protocol classes is the *pysmo* way. Let's further assume
our task is to calculate the great circle distance (gcd) between the station and the
event in both the traditional and pysmo way.

The traditional approach would be to write the gcd function to work specifically with the
data class. This means we need to know where and under what names the station and event
coordinates are stored inside the class. We can then calculate the gcd by passing an
instance of this class to the *f{sub}`traditional`* function.

Using pysmo, we write the gcd function to work with two sets of coordinates instead.
Specifically, two objects that match the `Location` type of pysmo serve as input for
*f{sub}`pysmo`*. Any class that has the attributes `latitude` and `longitude` matches the
`Location` type, which we assume are present in the *Station* and *Event* components of
the example data class. A graphical representation of the two approaches is shown in
({numref}`fig_hypothetical_file`).


```{figure} images/hypothetical_file.png
:name: fig_hypothetical_file

A hypothetical _generic class_ (shown in light green) contains within it station data
(light purple), event data (light yellow), and a seismogram (light red). Instead of
consuming the entire data class, pysmo functions (via protocol classes) only use the
information they actually need for a calculation and ignore the rest. Here the Station
and Event both match the Location type (light blue), and can therefore be used as input
for the *f{sub}`pysmo`* function. The *f{sub}`traditional`* function was specifically
written for the data class, so it will naturally accept the class as input data.
```

In the above example the same input object is used to provide data for both the
traditional and the pysmo functions, and both of them are able perform the task of
calculating the great circle distance equally well. Besides having a slightly different
syntax (which we believe to be a good thing in of itself), there appears to be no major
difference between the two methods. However, if we assume a slightly different
hypothetical data class, still containing the same information but in a different
format the, traditional function likely can no longer be used. On the other hand,
provided the new `Station` and `Event` formats still match the `Location` protocol, this
new data class still works with *f{sub}`pysmo`* ({numref}`fig_hypothetical_file2`).

```{figure} images/hypothetical_file2.png
:name: fig_hypothetical_file2

Because a different format is being used (represented by dark colours instead of light),
the function *f{sub}`traditional`* no longer is able to perform the calculation. The
pysmo function *f{sub}`pysmo`* still works, provided the new station and event
information format also still match the `Location` protocol.
```

To be fair, this apparent advantage of the pysmo function over the traditional one does
not come for free, as the underlying generic classes need to be compatible with the
protocol classes (see <project:types-more.md#more-on-types>). Fortunately, if there is
indeed a need to expand a class to make it compatible with the pysmo types, the effort to
do so is fairly minimal (especially compared to writing or maintaining an entire class).
The task of ensuring compatibility with pysmo may be done by the class maintainer, within
pysmo, or even by pysmo users (in which case we encourage submitting a pull request to
the pysmo repository). Given it is hard to imagine a scenario where the number of
functions is not significantly higher than the number of classes used, placing the
"burden of compatibility" on the class rather than the functions makes a lot more sense.
In a scenario where one has two types of data classes and 100 functions, it is far less
work to modify or extend the two existing class to match protocols than it is to code
those 100 functions so that they work with both classes (or write duplicate functions for
each class). And what if at some point in the future a third data class needs to be
supported?

Besides minimising potential compatibility problems, working with pysmo types also opens
up interesting ways of working with seismological data. We illustrate some in
{numref}`fig_pysmo_benefits`.

```{figure} images/pysmo_benefits.png
:name: fig_pysmo_benefits

Examples of how pysmo functions can be used in novel ways: (a) If a function needs
data that is not present in a file format, the file can be used in combination with
external data to perform the computation. (b) Using synthetic seismograms with pysmo
functions is straightforward, as there is no need to add all the extra (meta)data to
turn it into a particular file format for further use. (c) Functions can directly
use data from different file types in the same function.
```


### Using pysmo types

Once [installed](project:installation.md#installing-pysmo), the pysmo types can be
imported and used just like any class. For example:

```python
>>> from pysmo import Seismogram
>>>
>>> def my_func(my_seis: Seismogram) -> float:
...     """Return the sampling rate of a seismogram"""
...     return my_seis.sampling_rate
```

One thing to keep in mind, is to only ever use attributes and methods defined by the
types. For example, pysmo provides a `SAC`{l=python} class which reads sac files and
gives access to the seismogram data and all sac headers. It is also a subclass of
`Seismogram`{l=python}, so one might be tempted writing the above function using
`delta`{l=python} instead of `sampling_rate`{l=python}:

{emphasize-lines="6"}
```python
>>> from pysmo import SAC, Seismogram
>>>
>>> def my_bad_func(my_seis: Seismogram) -> float:
...     """Return the sampling rate of a seismogram"""
...     # We replace "sampling_rate" with "delta"
...     return my_seis.delta
...
>>> my_sac = SAC.from_file("file.sac")
>>> # this will print the sampling rate, but only for a SAC file
>>> print(my_bad_func(my_sac))
```

This will run without error, but now we an attribute specific to the SAC type is being
used. It is therefore not possible to guarantee the function will run with anything other
than a SAC object, and a good source code editor or mypy will flag it accordingly.

:::{tip}
Testing code for typing errors with mypy is as simple as running:

```bash
$ python -m mypy mycode.py
```
:::


## Compatible Classes

Using pysmo types requires compatible classes that hold the actual data. In order to be
compatible with a particular type, a class needs to have all the attributes and methods
(with the correct type!) as defined by that particular protocol class. These classes may
also possess additional attributes and methods that are not in the protocol classes, or
may even be compatible with multiple types.

The classes shipped with pysmo are described in the
[Classes](<project:classes.md#classes>) chapter.

## Available Types

```{eval-rst}
.. autosummary::

   pysmo.Hypocenter
   pysmo.Location
   pysmo.Seismogram
   pysmo.Station
```

```{eval-rst}
.. autoclass:: pysmo.Hypocenter
    :members:
    :inherited-members:
    :undoc-members:

.. autoclass:: pysmo.Location
    :members:
    :undoc-members:

.. autoclass:: pysmo.Seismogram
    :members:
    :undoc-members:

.. autoclass:: pysmo.Station
    :members:
    :inherited-members:
    :undoc-members:
```



[^dataclass]: In this discussion "data classes" simply refers to a class containing
(seismological) data, and not the Python [dataclasses module](inv:python#dataclasses)
