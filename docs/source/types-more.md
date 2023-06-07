# More on Types

(what-is-type)=
## What is (or isn't) a type?

A challenge we face when deciding if something can be described as a type arises, when
the actual data we want to store as this type are themselves calculated. If they are
calculated, can they really be classified as a type? Ideally no, but sometimes we may
find ourselves in a sort of chicken and egg situation. For example, if the coordinates of
an earthquake epicentre are determined using travel times, the great circle distance is
first calculated and then converted into coordinates. As the conversion depends on making
assumptions about the shape of the Earth (i.e. which reference model is used), the
epicentre location might be subject to change. Conversely, if the coordinates are known
first and then converted to distance, the opposite is the case.

Admittedly this would be more problematic if we were to design a class that contains
attributes for station and event coordinates, as well as epicentral distance. In such
instances one has to constantly recalculate dependent attributes when changing some other
one, check for consistency etc. However, even if we split such a class up into multiple
different ones, we might end up in a similar situation. It is therefore important that
pysmo types remain independent from each other. This holds true even when we measure
something directly; it might seem reasonable to define a type for this measured data,
but if it conflicts with an existing type we will run into trouble somewhere down the
road.

Because pysmo types are intentionally narrow in scope, the need to define new ones is
very likely to arise. When doing so, please keep the following in mind:

1. Avoid inconsistencies: As shown in the example above, the relationship between
   dependent variables can be ambiguous. Changing one variable means the other one
   needs to be updated too, and if it is not always done the same way the data may
   become inconsistent. The only solution is to ensure these updates are indeed
   always performed in the exact same manner, at which point the reason to
   incorporate these variables in the first place (flexibility) becomes mute.
2. Not blurring the lines between data and processing: Any change to the data
   stored in an object should be the direct result of processing, and not some
   adjustments made invisibly to the user.
3. Simplicity: The easier a data class is to understand, the easier it is to use.

:::{note}
Our concern is specifically with regards to _setting_ attribute values. Read-only
attributes or methods aren't particularly worrisome.
:::

Similarly, we believe data should be completely unambiguous. A good example for this is
how time is often handled in seismic data; for certain tasks it may make sense to use
different _kinds_ of time (e.g. relative to an event, first arrival, etc.), but in most
cases this introduces unnecessary complexity and potential for bugs (what if different
kinds of times are accidentally mixed?). Pysmo only uses absolute time, and instead
relies on Python's powerful libraries for any calculations that may become necessary.
This applies to units as well. Even if it may break with conventions, we always use
[SI units](https://en.wikipedia.org/wiki/International_System_of_Units).


## Compatibility with Generic Classes

A typical workflow using any kind of data consists of first reading these data into a
Python object, and then working with the attributes and methods provided by the object.
When reading a file, the attributes often mirror the way the data are organised within
the file, and are manipulated via the built-in methods or extra functions that use the
entire object as input ({numref}`fig_typical_class`).

```{figure} images/typical_class.drawio.png
:name: fig_typical_class

Relationship between Python objects and files storing data.
```

So if the data as described by the file format were to contain a variable called `S`
for storing the sampling rate, the same data will likely be present as an attribute
called `S` in the Python object. Besides the data, the Python object also needs to
incorporate logic to ensure the formatting and behaviour remains consistent with the
original file format. This is not only to be able to write back to the file, but also
because some variables might not be independent (see [above](<#what-is-type>)).

:::{hint}
There is sometimes confusion about the difference between an object and a class.
Classes are essentially blueprints used to create objects, and an object is an
instance of a class. For example, if we assign values to the variables `a = 2.5`{l=python}
and `b = 3.0`{l=python}, they are two separate instances (i.e. objects) of the same
class ([`float`{l=python}](inv:python#float)).
:::

These kinds of Python classes can be quite sophisticated, and often become the
centrepieces of Python modules. They may even be capable of reading and writing to
several different file formats. As one might imagine, writing and maintaining these
classes is a lot of work, and it does not make much sense to create yet another one
for pysmo. If we want to make use of these existing classes, we must ensure
compatibility with [pysmo types](project:types.md#types) as is depicted in
{numre}`fig_pysmo_layer`. Crucially, this requires only a fraction of work compared
to writing a data class from scratch.

({numref}`fig_pysmo_layer`).


```{figure} images/pysmo_layer.drawio.png
:name: fig_pysmo_layer

(a) An existing data class, when used as input for Pysmo functions, will
likely **not** be compatible with the function.
(b) After extending the data class it becomes compatible with more Pysmo
functions.
```

TODO: How to create a compatible class....
