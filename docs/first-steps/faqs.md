---
icon: lucide/circle-question-mark
tags:
  - First steps
---
# Frequently asked questions

## What is pysmo?

Pysmo is a Python library for seismology that defines lightweight
[Protocol][typing.Protocol]-based *types* describing what seismic data looks
like, without prescribing how it must be stored. Any class that matches a pysmo
type — regardless of where it comes from — can be used with pysmo functions.
This makes your code more modular, more reusable, and easier to maintain.

## How does pysmo relate to ObsPy?

Pysmo is designed to complement existing tools rather than replace them. If you
already use a library like [ObsPy](https://obspy.org), you can continue doing
so and adapt its classes to conform to pysmo types. This lets you benefit from
both ecosystems: the rich functionality of the other library, and the clean,
type-safe interfaces that pysmo provides.

## Do I need to rewrite my existing code to use pysmo?

No. Pysmo types are [Protocol][typing.Protocol] classes, which means any class
that has the right attributes and methods is automatically compatible — there is
no need to inherit from a pysmo base class. In many cases, minor adjustments to
an existing class are all that is needed for it to conform to a pysmo type.
Crucially, these adjustments are purely additive, so they will not break any
code that already uses the class.

## What does pysmo *not* do?

Pysmo is a library, not a framework. It does not impose a particular workflow,
manage data downloads, or provide a full processing pipeline. Its scope is
deliberately narrow: define types, and provide functions that operate on those
types. Everything else — how you store your data, where you fetch it from, how
you orchestrate your processing — is up to you.

## Pysmo seems hard. Is it really worth learning?

Pysmo relies heavily on standard Python concepts — type hints,
[Protocol][typing.Protocol] classes, and dataclasses. These are not
pysmo-specific; they are part of modern Python and are widely used across the
broader Python ecosystem. Learning to use them effectively will improve your
Python skills in general, regardless of whether you continue using pysmo.

!!! tip

    Pysmo does make use of typing features that go beyond basic type
    annotations. Python's type system has progressed considerably in recent
    versions, and pysmo leans into that. You do not need to fully understand
    these features to use pysmo, but they are what allow your editor or type
    checker to catch errors before you even run your code. The
    [first steps](index.md) page and the [tutorial](tutorial.md) walk through
    these ideas step by step.

## When does pysmo really shine?

Pysmo is at its best when you are writing *new* code and want it to be reusable
across different projects, data sources, or storage formats. If the
application-specific classes conform to pysmo types, you only need to write
shared processing steps once. Over time you may even find that you — or someone
else — have already written a function that does exactly what you need.

Because pysmo types are much smaller than a typical monolithic seismogram class,
populating them does not require a single file that contains everything. Instead,
individual attributes can be sourced from wherever makes sense — a database, a
web service, local files, or any combination of the above. Pysmo does not need
to anticipate every possible way data might be structured in the future — new
challenges and new data formats can be accommodated simply by writing classes
that conform to the existing types.

## Does pysmo enforce types at runtime?

No. Pysmo uses Python's type hinting system, which is checked *statically* by
tools like [mypy](https://mypy.readthedocs.io) or your IDE — not at runtime.
This means Python will not stop you from passing the wrong type to a function,
but a type checker will warn you before you ever run the code. If you need
runtime validation, consider pairing pysmo with a library like
[attrs](https://www.attrs.org),
[beartype](https://beartype.readthedocs.io), or
[pydantic](https://docs.pydantic.dev).

!!! note

    While pysmo *types* do not perform runtime checks, some of the classes and
    functions shipped with pysmo do validate their inputs at runtime. The
    distinction is that the types define an interface for static analysis,
    whereas the concrete implementations may choose to enforce constraints
    when they are actually used.

## What if no pysmo type fits my data?

Pysmo types are intentionally minimal, so they cover the attributes that are
common across a wide range of use cases. If your data has additional attributes,
you can simply add them to your own class alongside the pysmo-compatible ones —
pysmo only cares that the required attributes are present, not that they are the
*only* ones. If you believe a new type would benefit the wider community, feel
free to propose one on [GitHub](https://github.com/pysmo/pysmo).

## Where can I get help?

If you get stuck or have a question, the best place to ask is on the pysmo
[GitHub Discussions](https://github.com/pysmo/pysmo/discussions) page. For bug
reports or feature requests, please open an
[issue](https://github.com/pysmo/pysmo/issues).

## How can I help?

Pysmo is an open source project and welcomes contributions of all kinds —
whether that is asking questions, reporting bugs, or writing code. Head over to
the [contributing guide](../development/contributing.md) to find out how you can
get involved.
