---
icon: lucide/box
tags:
- Classes
- Usage
---
# External Classes

The [tutorial](../first-steps/tutorial.md) and the section on
[mini classes](./mini-classes.md) show how easy it is to write a bespoke class
for use with pysmo. However, you may already be committed to using an existing
class (e.g. because you need to do some processing in another framework). This
chapter discusses this scenario.

## Does a class work with pysmo?

Before answering this question, remember that pysmo types are typically very
simple. Most likely an individual type will contain way fewer attributes than
any third party class. You must therefore decide which types you want to use
with the class. Some may work out of the box, others may require some extra
work (e.g. because the attribute name or data format are different), and some
will never work (perhaps because the necessary data aren't in the class to
begin with).

!!! warning

    Keep in mind, that pysmo types merely define the interface, not the
    implementation. If the external class does something internally that
    differs from the expected behaviour (this could be something as simple as
    using different units) you might end up with issues.

### Yes

If the external class has the same attributes (name and type) as a given pysmo
type, then it should work out of the box. You can verify this using
[`isinstance`][]:

<!-- skip: start -->

```python
>>> from pysmo import Location
>>> isinstance(my_external_object, Location)
True
>>>
```

<!-- skip: end -->

This is most likely to happen with simpler types like
[`Location`][pysmo.Location], which only requires `latitude` and `longitude`
attributes of type [`float`][].

### Yes, with a tiny bit of work

The most common reason a class doesn't match a pysmo type is that the
attribute names differ. For example, a class might store a station latitude in
an attribute called `stla` instead of `latitude`. In such cases, you can
create a thin subclass that maps the existing attributes to the expected names
using Python [properties](https://docs.python.org/3/library/functions.html#property):

<!-- skip: next -->

```python
class MyExtendedClass(ExternalClass):
    @property
    def latitude(self) -> float:
        return self.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self.stla = value

    @property
    def longitude(self) -> float:
        return self.stlo

    @longitude.setter
    def longitude(self, value: float) -> None:
        self.stlo = value
```

This pattern is lightweight: the subclass inherits everything from the
original class and only adds the property aliases needed for pysmo
compatibility. Changing the aliased attributes also changes the originals and
vice versa. A concrete example of this pattern can be found in the
[`SAC`][pysmo.classes.SAC] API documentation.

### Yes, with a bit more work

Sometimes simple property aliases are not sufficient. This typically happens
when:

- **The same class needs to match the same type more than once.** For example,
  a class that stores both station and event coordinates cannot simply alias
  both to `latitude` and `longitude`, as the names would clash.
- **The data format differs.** The external class might store a time as a
  float (seconds since some reference), while pysmo expects a
  [`datetime`][datetime.datetime] object.
- **Some attributes are optional in the external class but required by the
  pysmo type.** You may need to add validation logic in the property getter.

In these cases, the recommended approach is to use **helper classes**. A helper
class is a small class that holds a reference to the parent object and provides
pysmo-compatible attribute access via properties:

<!-- skip: next -->

```python
class StationLocation:
    def __init__(self, parent: ExternalClass) -> None:
        self._parent = parent

    @property
    def latitude(self) -> float:
        if self._parent.stla is None:
            raise ValueError("Station latitude is not set")
        return self._parent.stla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._parent.stla = value

    # longitude property omitted for brevity...
```

<!-- skip: next -->

```python
class EventLocation:
    def __init__(self, parent: ExternalClass) -> None:
        self._parent = parent

    @property
    def latitude(self) -> float:
        if self._parent.evla is None:
            raise ValueError("Event latitude is not set")
        return self._parent.evla

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._parent.evla = value

    # longitude property omitted for brevity...
```

Both `StationLocation` and `EventLocation` match the
[`Location`][pysmo.Location] type, while avoiding name clashes because each
helper class has its own namespace. Because they reference the parent object,
changes made through a helper class are reflected in the parent and vice versa.

With the helper classes in place, they can be added as attributes to a new
class that inherits from the external one:

<!-- skip: next -->

```python
class MyExtendedClass(ExternalClass):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.station_location = StationLocation(parent=self)
        self.event_location = EventLocation(parent=self)
```

## Example

The pysmo package itself uses this pattern for the
[`SAC`][pysmo.classes.SAC] class. The underlying
[`SacIO`][pysmo.lib.io.SacIO] class manages file I/O and provides access to
all SAC header fields using their original names (`stla`, `evla`, `b`, etc.).
These names do not match pysmo types, and several types (station location,
event location, seismogram data) coexist within a single object.

The [`SAC`][pysmo.classes.SAC] class solves this by inheriting from
[`SacIO`][pysmo.lib.io.SacIO] and adding helper class attributes. While
[`SacIO`][pysmo.lib.io.SacIO] itself comprises roughly 800 lines of code,
the adaptation layer in [`SAC`][pysmo.classes.SAC] is only around 200 -
typically it is much less work to adapt an existing class than what went into
building it in the first place:

```python
>>> from pysmo import Seismogram, Station, Event
>>> from pysmo.classes import SAC
>>> sac = SAC.from_file("example.sac")
>>> isinstance(sac.seismogram, Seismogram)
True
>>> isinstance(sac.station, Station)
True
>>> isinstance(sac.event, Event)
True
>>>
```

For more details, see the [`SAC`][pysmo.classes.SAC] API documentation.
