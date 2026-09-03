---
tags:
  - Usage
---

# Usage

Pysmo is as much an opinionated way of writing code as it is a library. The
[first steps](../first-steps/index.md) chapter introduces its types and shows
them in use. This chapter covers the reasoning behind them and how they work
internally, as a guide to writing code in the same style. For details on a
specific component, see the [API reference](../api/pysmo.md).

## Library or framework

Before taking on a third-party package, it is worth asking whether it is a
library or a framework:

- A library is a set of building blocks for solving a larger problem or building
    an application.
- A framework is a ready-made solution to a class of problems, often close to an
    application in its own right.

The line is not always sharp. It depends not only on what the authors intended,
but on how the package is used. A useful question, and one that matters for
keeping code maintainable, is how heavily the code depends on the package:

- How exposed is the code to future changes in the package? Using only its
    built-in features is fairly safe. Building new features on top of it, such
    as new processing functions, is more fragile.
- Is it clear what the package does, or does a given class or function behave
    like a black box? This often comes down to how tightly its components depend
    on one another.
- Does it work well alongside other packages and data formats?
- Could it be swapped for a similar package, or a bespoke implementation,
    without much trouble?
- Does relying on it rule out things like porting the code to another language?

It usually comes down to a trade-off between convenience and transparency. The
core of pysmo sits on the library side. A few parts lean more towards a
framework, and pysmo separates them by namespace: the more application-like
modules live in [`pysmo.tools`][], and everything else stays library-like.

!!! note "Tools are reusable too"

    The split is about organisation, not lock-in. Each `pysmo.tools` module is
    written against the pysmo types and takes ordinary arguments, so any one can be
    used on its own with a conforming class. They also double as worked examples of
    the style this section describes.
