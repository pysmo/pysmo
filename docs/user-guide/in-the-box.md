# What is in the Box?

## Library vs. Framework

Before getting into what is included in the pysmo package, we briefly want to
discuss what we mean by "library" and "framework" within the context of pysmo
(or even within software in general). We use the following definitions:

- Libraries serve as building blocks to solve more complex problems or
  for building applications.
- Frameworks provide ready-made solutions to solve complex problems. A
  framework may easily also be considered an application.

Distinguishing between the two can be a bit tricky when it comes to using third
party tools like pysmo. Often it is not only a question of what the respective
authors intend their software to be, but also how you use it for your purposes.
A helpful way of looking at this (and an important consideration for future
proofing your code), is to ask yourself in which ways your code depends on the
third party package you are using. By this we mean factors such as:

- Do you understand what a particular package does, or does it feel more like
  a black box when you e.g. call a function from that package?
- Does the third party package play nicely with other packages or data formats?
- Can it easily be replaced by a similar package (or your own implementation)?
- Does using a particular package make it impossible to e.g. rewrite your
  code in a different programming language?

Often it boils down to a trade-off between convenience and transparency, and
which side if it you find yourself on more. With that said, we consider the
core of pysmo to be very much a library. Outside that core part, there are some
extra bits that fall more on the framework side of things. To accommodate for
that, pysmo organises things into different namespaces (as we show below).

## Package contents

At the heart of pysmo will always be the pysmo types which, according to the
above definitions, constitute a library that you can use in your own code. As
any code written using pysmo types will often be reusable, we also include such
code for use in a more framework-like setting. In other words, you don't need
to reinvent the wheel in order to use pysmo. Aside from the [types](./types.md)
you can find the following in the psymo package:

- [Classes](./classes.md): used to store data in a way that conforms
  with pysmo types, and can therefore be used as input for functions that
  expect pysmo types. As there is a strong relationship with the pysmo types,
  the pysmo package includes reference classes for each type. These reference
  classes are minimal implementations of pysmo type compatible classes, and are
  thus named with a `Mini` prefix
  (e.g. [`MiniSeismogram`][pysmo.MiniSeismogram]). The `Mini` classes are in
  the base ([`pysmo`](../reference/base.md)) namespace, while others are in
  [`pysmo.classes`](../reference/classes.md).
- [Functions](./functions.md): basic functions used to manipulate data that is
  stored in the classes described above. They are imported from the
  [`pysmo.functions`](../reference/functions.md) namespace.
- [Tools](../reference/tools.md): provide the framework-like functionality described above.
  This is for example grouping of functions belonging to a particular topic,
  or providing more complex workflows (typically building on top of the
  basic functions or other tools). In order to use a particular tool, you must
  import it via `pysmo.tools.<tool-name>`.

!!! tip "Package namespaces"

    Package namespaces are a way to keep things organised and to avoid name
    collisions (which is why you should avoid using `import *` statements in
    Python). As for pysmo, the main reason for breaking things up into multiple
    namespaces is to make it easy to add new functionality to pysmo without
    the need to edit existing code. As a user this simply means you may need to
    occasionally use more than one `import` statement at the begining of your
    scripts.
