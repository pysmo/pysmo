---
icon: lucide/save
tags:
  - Classes
  - Usage
---

# Serialisation

A [bespoke](./bespoke-classes.md) or [Mini](./mini-classes.md) seismogram exists
only as long as the Python process holding it. It needs a form that survives
past that process, and a way back from that form into an equivalent object.

Pysmo has no single class every seismogram is built from.
[`Seismogram`][pysmo.Seismogram] is a protocol. Any class with the right
attributes satisfies it, so there is no one privileged type to anchor a native
file format on. Pysmo provides functions to save a seismogram as JSON instead, a
format generic enough to describe any of them, and to restore one from it. This
chapter covers how that works and where its limits are.

!!! info "Why not pickle?"

    Python's own [`pickle`][] module can serialise almost any object, with no extra
    code needed. Rather than just storing values, it stores instructions for
    rebuilding the object, and carries those out again when loading. Pickle exists
    for exactly that convenience, and is a reasonable choice when the file's origin
    is already known and trusted.

## Not every seismogram qualifies

Satisfying the [`Seismogram`][pysmo.Seismogram] protocol only guarantees the
right attribute names and types. It says nothing about a class's internals, so
nothing beyond that can be assumed about how it behaves (the same gap is covered
in [Structure, not meaning](./bespoke-classes.md#structure-not-meaning)).

Saving a seismogram and reading it back is one behaviour that depends on
internals. Writing a document means reading each attribute's actual stored
value. Rebuilding an object means writing straight back into it. That only works
when the attributes are real, stored fields, not something computed or fetched
on access.

This works well with `attrs` classes, since their fields are declared as real,
stored attributes by design. `attrs` is used throughout pysmo, so in practice
this rarely narrows what's usable.

A live view such as [`SacSeismogram`][pysmo.classes.SacSeismogram] does not
qualify. Its `data` is a property that reads and writes straight through to the
underlying [`SacIO`][pysmo.lib.io.SacIO] instance's own stored field, rather
than holding a stored array of its own. That is also why it cannot rebuild
through pysmo's `replace` pattern (detail in
[What `replace` and `copy` assume](./bespoke-classes.md#what-replace-and-copy-assume)).
That doesn't mean it has no way to reach disk. The same `SacIO` instance can
still write a full SAC file directly, which is exactly what
[`SAC.write`][pysmo.classes.SAC.write] does.

Writing and maintaining a bespoke read/write layer for every custom class is
exactly the tedium saving a seismogram as JSON exists to avoid. Building a
bespoke class on `attrs`, the way
[Validation and conversion](./bespoke-classes.md#validation-and-conversion)
already recommends, is what keeps it eligible for that.

## Round-tripping a seismogram

[`seismogram_to_json`][pysmo.functions.seismogram_to_json] saves a seismogram
*instance*, not just its values, into a JSON document. The document holds three
fields:

- `cls`: the seismogram's class, recorded as `module:qualname`, e.g.
    `pysmo:MiniSeismogram`.
- `v`: a version number for the payload's shape, so a document from an
    incompatible version can be refused instead of misread.
- `payload`: every field the concrete class declares, not only the three the
    `Seismogram` protocol requires.

The result is plain bytes, moved to and from a file with the ordinary
[`Path.write_bytes`][pathlib.Path.write_bytes]/[`Path.read_bytes`][pathlib.Path.read_bytes]
pair. [`seismogram_from_json`][pysmo.functions.seismogram_from_json] restores
the instance. It parses the document, imports the recorded class, and rebuilds
it from the payload:

```python
>>> import pandas as pd
>>> import tempfile
>>> from pathlib import Path
>>> from pysmo import MiniSeismogram
>>> from pysmo.functions import seismogram_from_json, seismogram_to_json
>>>
>>> seismogram = MiniSeismogram(
...     begin_time=pd.Timestamp("2024-01-01T00:00:00Z"),
...     delta=pd.Timedelta(seconds=1),
...     data=[1.0, 2.0, 3.0],
... )
>>> blob = seismogram_to_json(seismogram)  #(1)!
>>> path = Path(tempfile.gettempdir()) / "seismogram.json"
>>> _ = path.write_bytes(blob)  #(2)!
>>> loaded = seismogram_from_json(path.read_bytes())  #(3)!
>>> loaded == seismogram
True
>>>
```

1. Encode the instance into a JSON document, as bytes.
2. Save it like any other file.
3. Read it back and restore an equivalent instance.

By default, restoring a seismogram returns the same type it was saved with,
since `seismogram_from_json` imports the class recorded in the document. Passing
`cls` makes that choice explicit rather than implicit:

```python
>>> seismogram_from_json(blob, cls=MiniSeismogram).data.tolist()
[1.0, 2.0, 3.0]
>>>
```

`cls=MiniSeismogram` here names the same class already recorded, so nothing
about the rebuilt instance changes. What narrows is the return type, from the
`Seismogram` protocol down to `MiniSeismogram` itself.

!!! tip "Restoring into a different class"

    `cls` structures the payload into whatever type is named, not only the one
    recorded, so a document saved as one class can be restored into a different one.
    This only works when the payload already supplies every field the target class
    requires. A mandatory field the payload doesn't have makes
    `seismogram_from_json` raise `TypeError` for a payload that doesn't fit.

`seismogram_to_json(seismogram, verify=True)` decodes the document it just
produced and compares it back to `seismogram`, raising `TypeError` on any
mismatch. It catches a narrower failure than the round trip simply not working.
A conversion hook can silently drop information and still produce a valid but
unfaithful document, a tuple tucked into
[`MiniIccsSeismogram.extra`][pysmo.tools.iccs.MiniIccsSeismogram.extra] decoded
back as a list:

```python
>>> from pysmo.tools.iccs import MiniIccsSeismogram
>>> lossy = MiniIccsSeismogram(
...     begin_time=seismogram.begin_time,
...     delta=seismogram.delta,
...     data=seismogram.data,
...     t0=seismogram.begin_time,
...     extra={"note": (1, 2, 3)},
... )
>>> seismogram_to_json(lossy, verify=True)
Traceback (most recent call last):
...
TypeError: ...
>>>
```

## Doing it safely

`seismogram_from_json` never executes anything a document supplies. It only ever
constructs a class it already knows how to build. A document's `cls` field is
still just a string. Nothing in the format stops it naming any importable
module:

```python
>>> import json
>>> tampered = json.dumps(
...     {"cls": "os:system", "v": 1, "payload": {"command": "rm -rf ~"}}  #(1)!
... ).encode()
>>> seismogram_from_json(tampered)
Traceback (most recent call last):
...
TypeError: ...
```

1. The command an attacker would want run.

`trusted_modules` is the allowlist `seismogram_from_json` checks the recorded
module against before doing anything else. It defaults to `("pysmo",)`. `os` is
not in it, so the attempt fails before `payload`, command and all, is ever read.

The same gate does not care about intent. A harmless class living outside
`trusted_modules` is refused exactly the same way:

```python
>>> import numpy as np
>>> import attrs
>>> @attrs.define
... class LocalSeismogram:
...     begin_time: pd.Timestamp
...     delta: pd.Timedelta
...     data: np.ndarray
...
>>> local = LocalSeismogram(
...     seismogram.begin_time, seismogram.delta, np.array(seismogram.data)
... )
>>> local_blob = seismogram_to_json(local)
>>> seismogram_from_json(local_blob)
Traceback (most recent call last):
...
TypeError: ...
```

Two things get past that gate deliberately: naming the module in
`trusted_modules`, or passing `cls` outright, which skips the check entirely
because the type is already known rather than looked up by name.

```python
>>> seismogram_from_json(local_blob, cls=LocalSeismogram).data.tolist()
[1.0, 2.0, 3.0]
```

!!! danger "Pickle can't be gated the same way"

    As a pickle, that document would not just name `os.system`. It would call it,
    with `rm -rf ~` as the argument, the moment the file loaded. Once a module is
    trusted, pickle can invoke any callable inside it with payload-supplied
    arguments, not only construct a known class from fixed fields.

## Known limits

An untyped `dict[Hashable, Any]` field, `MiniIccsSeismogram.extra` for instance,
is passed through shallowly. Its keys and values need to already be JSON
primitives, lists, or nested dicts of the same. Anything richer than that, a
tuple, say, is silently lossy rather than rejected up front. `verify=True` is
what catches it.

The document's `v` field is pinned to the format's current version.
`seismogram_from_json` refuses anything outside the versions it still
understands, rather than guessing at a shape that has since changed. The version
bumps on any change to the payload shape or the leaf hooks above.

Pickle remains a valid option when these limits matter. Its trust requirement is
no obstacle inside a fully controlled pipeline. One process writes what it alone
reads back. A bespoke class may still need a lossless, versioned document
outside that boundary. It is then back to the tedium this format exists to avoid,
left to write its own round-trip logic.
