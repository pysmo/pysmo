# Frequently asked questions

## What are pysmos use cases

There is actually no specific use case for psymo; the main purpose of pysmo is
to serve as a library when writing *new* code, which means when and how to use
pysmo is essentially up to you to decide. To help with this, pysmo has exactly
two priorities:

1. Focus on making the coding experience as intuitive and pleasant as possible
   (proper typing, autocompletion, etc.).
2. Ensure code can be easily reused.

Priority (1) is probably fairly obvious. As for (2), consider for example two
applications that store data in different ways internally (i.e. they define
their own types), but share some common steps in their processing flows. If you
ensure the application specific types match pysmo types, you only need to write
the common steps once for both applications. If you've been using pysmo for a
while already you may even find you unwittingly already wrote a function that
does just what you need (or someone else may have written it)!

!!! note

    If an application or framework that solves your problem already exists,
    there is little reason to use pysmo (though you might find it useful to
    use existing frameworks in combination with pysmo). Note also that from
    pysmo's perspective, there is little difference between an application
    and a framework - they both typically user their own particular structures
    for storing and processing data.
