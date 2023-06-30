# Classes

The types discussed in the [previous chapter](<project:types.md#types>) are only useful
in conjunction with compatible classes. A class is is compatible with a particular type
if all attributes and methods present in the type (defined by the respective protocol
class) are also present in the class itself. For example, a `City`{l=python} class may
look something like this:

```python
# file: city.py
from dataclasses import dataclass


@dataclass
class City:
   name: str
   founded: int
   latitude: float
   longitude: float
   elevation: float
```

As the `City`{l=python} class has `latitude`{l=python} and `longitude`{l=python}
attributes, an instance of it is also an instance of the
[`Location`{l=python}](<project:types.md#pysmo.Location>) type:

```bash
$ python -i city.py
>>> from pysmo import Location
>>> nyc = City(name='New York', founded='1624', latitude=40.7, longitude=-74, elevation=10)
>>> isinstance(nyc, Location)
True
```

This example also illustrates that a class may contain additional attributes and methods
that are not part of the type definition. In fact, a class may even match multiple types!

:::{warning}
In cases where a class contains additional attributes or methods, we strongly suggest to
never access these in e.g. a function using pysmo types as input. For example, the code
below will run if the `city` input is an instance of the `City` class (because it has the
`name` attribute). However, the `name` attribute may not be present in another class that
matches the [`Location`{l=python}](<project:types.md#pysmo.Location>) type, resulting in
a runtime error when this function is called.

```python
# Do not do this!
def print_coordinates(city: Location) -> None:
   print(f"The coordinates of {city.name} are: {city.latitude}, {city.longitude}")
```
:::


## Minimal Classes

Pysmo includes a minimal implementations of a class for each type. They are all named
using the pattern `Mini<Type>`, thus the
[`Seismogram`{l=python}](<project:types.md#pysmo.Seismogram>) type has a corresponding
[`MiniSeismogram`{l=python}](<project:classes.md#pysmo.MiniSeismogram>) class. The *Mini*
classes may be used directly to store and process data, or serve as base classes when
creating new or modifying existing classes.

```{eval-rst}
.. autoclass:: pysmo.MiniHypocenter
    :members:
    :inherited-members:
    :undoc-members:

.. autoclass:: pysmo.MiniLocation
    :members:
    :undoc-members:

.. autoclass:: pysmo.MiniSeismogram
    :members:
    :undoc-members:

.. autoclass:: pysmo.MiniStation
    :members:
    :inherited-members:
    :undoc-members:
```

## The SAC Class

[SAC](<https://ds.iris.edu/ds/nodes/dmc/software/downloads/sac/>) (Seismic Analysis Code)
is a commonly used program that uses it's own file format. Pysmo provides a Python class
to access SAC files.

```{eval-rst}
.. autoclass:: pysmo.SAC
    :members: Event, Station, Seismogram

.. autoclass:: pysmo.classes.sac._SacEvent
    :members:
    :inherited-members:

.. autoclass:: pysmo.classes.sac._SacSeismogram
    :members:
    :inherited-members:

.. autoclass:: pysmo.classes.sac._SacStation
    :members:
    :inherited-members:
```
