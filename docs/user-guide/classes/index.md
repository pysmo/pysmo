# Classes

The types discussed in the [previous chapter](../types.md) are only useful in
conjunction with compatible classes. A class is is compatible with a particular type
if all attributes and methods present in the type (defined by the respective protocol
class) are also present in the class itself. For example, a `City` class may look
something like this:

```python title="city.py"
from dataclasses import dataclass


@dataclass
class City:
   name: str
   founded: int
   latitude: float
   longitude: float
   elevation: float
```

As the `City` class has `latitude` and `longitude` attributes, an instance of it
is also an instance of the [`Location`][pysmo.types.Location] type:

<!-- termynal: -->

```python
$ python -i city.py
>>> from pysmo import Location
>>> nyc = City(name='New York', founded='1624', \
               latitude=40.7, longitude=-74, elevation=10)
>>> isinstance(nyc, Location)
True
```

This example also illustrates that a class may contain additional attributes and
methods that are not part of the type definition. In fact, a class may even match
multiple types!

!!! warning

    In cases where a class contains additional attributes or methods, we 
    strongly suggest to never access these in e.g. a function using pysmo 
    types as input. For example, the code below will run if the `city` input 
    is an instance of the `City` class (because it has the `name` attribute). 
    However, the `name` attribute may not be present in another class that
    matches the [`Location`][pysmo.types.Location] type, resulting in
    a runtime error when this function is called.

    ```python
    # Do not do this!
    def print_coordinates(city: Location) -> None:
       print(f"The coordinates of {city.name} are: {city.latitude}, {city.longitude}")
    ```
