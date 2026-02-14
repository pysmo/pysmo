---
icon: material/run
tags:
  - Motivation
  - Usage
---
# Motivation

Typing has become an increasingly important feature of modern Python. This has
changed how we write code, helped prevent errors, and improved the experience
working with modern editors. Pysmo brings these features to the field of
seismology.

!!! tip

    <a id="type-tip"></a>
    In the paragraphs below we use the terms "class" and "type" a lot. We can
    explore the relationship between these terms in more detail using the
    built-in [`float`][] type:

    ```python
    >>> a = 1.2 #(1)!
    >>> type(a) #(2)!
    <class 'float'>
    >>> type(float) #(3)!
    <class 'type'>
    >>>
    ```

    1. We first assign a float to the variable `a`.
    2. Then we verify it is indeed a float using the `type` command.
    3. The type of the float class is... a type!

    This example shows that the type of a class is itself a type, so every time
    we define a class in Python, we also define a type.

## The problem with types in seismology

Anyone who has taken a course on programming (in any language) will most likely
first have been taught about the different data types available. These typically
consist of simple types like integers, floats, strings, as well as the more
complicated arrays, dictionaries, etc. These types are typically very clearly
defined and intuitive to use. For example, we don't need to think very hard
whether or not it makes sense to pass the string "hello world" as input to a
program that calculates the square root of a number.

As one moves from general-purpose programming towards more specialised problem
solving (e.g. within a particular scientific field), the expected input and
output for a piece of code is likely to become more complex. We may therefore
quite easily reach a point where we no longer have that intuitive feeling about
the data we are working with.

When processing seismological data with Python, we naturally want to consider a
seismogram to be a Python type of sorts. However, which data that type should
include depends on the particular requirements of the processing that is
performed with that seismogram data. Thus, if we define a seismogram type based
on the needs of one particular application, it might not be suited for another.
If we attempt to account for many use cases by being as broad as possible when
defining a type, we are again more at risk of losing the intuitive feeling for
our type while writing code. This kind of seismogram type would just be an
abstract construct, rather than having any meaningful connection with how we
experience a seismogram in nature or when treating it mathematically (and still
wouldn't be able to guarantee it would work with all possible future use
cases!).

??? example "File formats in seismology"

    The challenges we face due to different file formats that exist in
    seismology, and how they are used for processing, are not dissimilar to
    what was discussed above. Their design naturally focuses on data storage,
    but they often try to cater towards applications too. We can use
    [SAC](https://ds.iris.edu/files/sac-manual/manual/file_format.html) as an
    example for this; SAC is essentially an application with its own file
    format. Additionally, SAC files are commonly used as input format for third
    party applications. This is possible because SAC files allow storing a lot
    of metadata in their "headers". The approach does have a few drawbacks
    though:

    - The majority of SAC headers are optional (only 6 are mandatory), so there
      is no guarantee they are actually set to a value. To prevent this from
      causing errors, checks need to be built into code to ensure they are
      actually set.
    - The large number of headers (over 150!) requires intricate knowledge of
      the file format. Even so, using SAC files probably feels far from
      intuitive.
    - SAC files are limited to the headers defined in the format. The only way
      to store custom data is via the "user defined headers", or if those run
      out, repurposing other headers to mean something else.

## The pysmo solution

As it is impossible to know all possible ways a seismogram might be used in the
future, defining an all-encompassing type for a seismogram for any use case is
equally impossible (and would be difficult to use anyway). Pysmo instead
focuses on what different seismograms have *in common* to define a seismogram
type. This leads to the following approach:

- Seismogram data are stored in any existing or new format (i.e. Python class).
  We might call this the "data seismogram". Recall also that any class in
  Python is also a type that can be used in type annotations.
- The attributes all seismograms have in common determine the pysmo type.
  Unlike the data seismogram, it is only used for type annotations, so it
  doesn't need to be a real class. As mentioned elsewhere,
  [`Protocol`][typing.Protocol] classes are used for this purpose.
- Code that requires access to specific attributes or methods of the data
  seismogram uses that as its type (i.e. as their type annotation).
- Code that only uses the parts of the data seismogram that all seismograms
  have in common uses pysmo types instead.

This approach gives complete freedom to store and use data in any way, while
still being able to write reusable code using pysmo types.

## Code writing experience

At this point it is worth remembering that type hints in Python are not enforced
at runtime. They are therefore most useful when used together with a modern
editor capable of interpreting these type hints. Typically this happens in the
form of autocomplete and error checking.

### Autocomplete

Once [installed](../first-steps/installation.md), the pysmo types can be
imported and used just like any class. We can, for example, use the
[`Seismogram`][pysmo.Seismogram] type to annotate a function. A modern editor
is then able to tell us what attributes are available for a variable and speed
up the coding process by offering autocomplete for the attributes:

![Editor Autocomplete](../images/editor_autocomplete_dark.png#only-dark)
![Editor Autocomplete](../images/editor_autocomplete_light.png#only-light)

### Error checking

Should we for some reason make coding errors such as trying to access a
non-existing attribute, the editor will give us a warning:

![Editor Error](../images/editor_error_dark.png#only-dark){ loading=lazy }
![Editor Error](../images/editor_error_light.png#only-light){ loading=lazy }

These kinds of warnings are not just for catching typos. They will also catch
programming errors such as trying to set the value of `delta` to a string
instead of a float.

!!! tip
    Should your editor for some reason be unable to parse type hints, testing
    your code for typing errors can still be done with
    [mypy](https://mypy.readthedocs.io/en/stable/) by running:

    ```bash
    $ python -m mypy mycode.py
    ```
