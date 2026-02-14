---
tags:
  - Usage
---
# Usage

Pysmo is just as much an opinionated way of writing code as it is a library.
This section of the documentation focuses on the philosophy and inner workings
of pysmo. This will help you write pysmo-like code using pysmo. If you are
looking for specifics on a particular component of pysmo, please refer to the
relevant section in the [API reference](../api/pysmo.md).

## Library vs. framework

Before using a third party package for your project, it is important to consider
if what you are using is a library or a framework. One might define them as
follows:

- Libraries serve as building blocks to solve more complex problems or for
  building applications.
- Frameworks provide ready-made solutions to solve complex problems. A
  framework may easily also be considered an application itself.

Distinguishing between the two can be a bit tricky when it comes to using tools
like pysmo. Often it is not only a question of what the respective authors
intend their software to be, but also how you use it for your purposes. A
helpful way of looking at this (and an important consideration for future
proofing your code), is to ask yourself in which ways your code depends on the
third party package you are using. By this we mean factors such as:

- How susceptible is your project to potential future changes in the package
  you are using? If you are only using built-in features you are probably safe,
  but if you are writing new features (e.g. new functions for data processing)
  they might suddenly stop working.
- Do you understand what a particular package does, or does it feel more like
  a black box when you e.g. use a particular class or call a function from that
  package? This is often influenced by how integrated or dependent individual
  components of that package are.
- Does the third party package play nicely with other packages or data formats?
- Can it easily be replaced by a similar package (or your own implementation)?
- Does using a particular package make it impossible to e.g. rewrite your
  code in a different programming language?

Often it boils down to a trade-off between convenience and transparency, and
which side of it you find yourself on more. With that said, the core of pysmo
is considered to be very much a library. Outside the core part, there
are some extra bits that fall more on the framework side of things. To
accommodate for that, pysmo organises things into different namespaces. More
application-like modules are found in [`pysmo.tools`][], while everything else
is library-like.

!!! note

    Even [`pysmo.tools`][] are written in a way that makes them easy to re-use
    outside of pysmo.
