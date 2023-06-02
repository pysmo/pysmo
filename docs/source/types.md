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

[Protocol classes](inv:mypy#protocols) were introduced in Python 3.8, and we invite you
to read [PEP 544](https://peps.python.org/pep-0544/) for an in-depth introduction. In
this section we detail how (and why) we use them in pysmo.

We are of the opinion that type matters. Therefore there ought to be meaningful
relationship between a class name and the information contained within that class. In the
above example we put a floating point number in a [`float`{l=python}](inv:python#float)
object. It is pretty much self-explanatory what the float class is for, and it seems
unlikely the definition of the float class is ever going to drastically change. If we
were to write a function that requires its input to be a floating point number, we can
simply make it a requirement that any input is of type
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

Our hypothetical data class [^dataclass] contains only a seismogram, station and event data.
Here, we consider using an instance of this class directly to be the *traditional*
approach, while using it via protocol classes is the *pysmo* way. Let's further assume
our task is to calculate the great circle distance (gcd) between the station and the
event in both ways. Using pysmo, we cherry pick the information we need and pass it the
function, while with the traditional approach we pass the entire object to the function
as input ({numref}`fig_hypothetical_file`).


```{figure} images/hypothetical_file.drawio.png
:name: fig_hypothetical_file

A hypothetical _generic class_ (green) contains within it station data (blue), event
data (yellow), and a seismogram (red). Instead of consuming the entire data class,
Pysmo functions (via protocol classes) only use the information they actually need
for a calculation and ignore the rest.
```

In the above example the same input object is used to provide data for both the
traditional and the pysmo functions, and both methods are able perform the task of
calculating the great circle distance equally well. Besides having a slightly different
syntax (which we believe to be a good thing in of itself), there appears to be no major
difference between the two methods.

Now, if we assume a different hypothetical data class, still with all the information
needed for the gcd calculation but in a different format and without seismogram data, the
pysmo function can still be used. The traditional function will fail because it is given
input data it is unable to parse properly
({numref}`fig_hypothetical_file_without_seismogram`).

```{figure} images/hypothetical_file_without_seismogram.drawio.png
:name: fig_hypothetical_file_without_seismogram

Because a different format is being used (purple instead of green), the traditional
function no longer is able to perform the calculation. The pysmo function still works,
provided station and event information are in a compatible format (the class as a
whole does not have to be compatible!).
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

Besides minimising potential compatibility problems, working with pysmo types also opens
up interesting ways of working with seismological data. We illustrate some in
{numref}`fig_pysmo_benefits`.

```{figure} images/pysmo_benefits.drawio.png
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


## Available Types

TODO:

- list available types and link to them.

## Compatible Classes

TODO:

- list available classes and link to them.
- explain how to add new ones


[^dataclass]: In this discussion "data classes" simply refers to a class containing
(seismological) data, and not the Python [dataclasses module](inv:python#dataclasses)
