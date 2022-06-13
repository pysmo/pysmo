Fundamentals
============

Data and Processing
-------------------
It can be challenging to decide if certain types of data are of a more fundamental kind,
or if they are perhaps better classified as results of processing (whereby the fundamental
kinds are used in the calculations). For example, if the coordinates of an Earthquake
epicentre are determined using travel times, the great circle distance is first calculated
and then converted into coordinates. As the conversion depends on making assumptions about
the shape of the Earth (i.e. which reference model is used), the epicentre location might
be subject to change. Conversely, if the coordinates are known first and then converted to
distance, the opposite is the case. In such instances it is therefore practically impossible
to say with certainty which types of data are more representative of the *real world* they
are describing. Thus, deciding which types of data should be included into something like
a Python data class or file format poses a challenge. There are two ways to deal with this:
(1) include all data types and thus be able to accommodate different scenarios, or (2)
decide which independent data types are most likely to be immutable and only use those.
In Pysmo we go with the later for the following reasons:

   #. Avoid inconsistencies: As shown in the example above, the relationship between
      dependent variables can be ambiguous. Changing one variable means the other one
      needs to be updated too, and if it is not always done the same way the data may
      become inconsistent. The only solution is to ensure these updates are indeed
      always performed in the exact same manner, at which point the reason to
      incorporate these variables in the first place (flexibility) becomes mute.
   #. Not blurring the lines between data and processing: Any change to the data
      stored in an object should be the direct result of processing, and not some
      adjustments made invisibly to the user.
   #. Simplicity: The easier a data class is to understand, the easier it is to use.

Similarly, we believe data should be completely unambiguous. A good example for this is how
time is often handled in seismic data; for certain tasks it may make sense to use different
*kinds* of time (e.g. relative to an event, first arrival, etc.), but in most cases this
introduces unnecessary complexity and potential for bugs (what if different kinds of times
are accidentally mixed?). Pysmo only uses absolute time, and instead relies on Python's
powerful libraries for any calculations that may become necessary.

Pysmo Data Types
----------------
A typical workflow using any kind of data consists of first reading these data into a Python
object, and then working with the attributes and methods provided by the object. When reading
a file, the attributes often mirror the way the data are organised within the file, and are
manipulated via the built-in methods or extra functions that use the entire object as input
(Fig. :numref:`fig_typical_class`).

   .. _fig_typical_class:
   .. figure:: images/typical_class.drawio.png
      :align: center

      Relationship between Python objects and files storing data.

So if the data as described by the file format were to contain a variable called ``S``
for storing the sampling rate, the same data will likely be present as an attribute called
``S`` in the Python object. Besides the data, the Python object also needs to incorporate
logic to ensure the formatting and behaviour remains consistent with the original file format.
This is not only to be able to write back to the file, but also because some variables might
not be independent. Should there also be an attribute for the end time, then it needs
changing whenever the sampling rate changes (and vice-versa). Finally, objects often contain
methods (built-in functions) that use the attributes to perform tasks.

.. note:: 
   There is sometimes confusion about the difference between an object and a class.
   Classes are essentially blueprints used to create objects, and an object is an
   instance of a class. For example, if we assign values to the variables ``a = 2.5``
   and ``b = 3.0``, they are two separate instances (i.e. objects) of the same
   class (``float``).

These kinds of Python classes can be quite sophisticated, and often become the centrepieces
of Python modules that can be installed as 3rd party packages on users computers. They may
even be capable of reading and writing to several different file formats. As one might imagine,
writing and maintaining these classes is a lot of work, and it does not make much sense to
create yet another one for Pysmo. However, we do not want to use these classes unconditionally.
That is because they typically either exactly mirror the file format they are based on, or
have a similarly all-encompassing scope. Rather than using a single class that contains all
possible kinds of information as input for Pysmo functions, we want to break these classes up
into multiple, more `atomic` types of data. The most basic types (e.g. float, integer, string,
etc.) already exist, of course. However, within a particular context (in this case Seismology),
we believe there exist data types that are similarly basic and unambiguous. In practice this
means simplifying the actual seismogram data by separating them from the metadata they were
stored together with (whereby the metadata themselves become independent types). We believe
that defining data this way is more representative of how things exist in the physical world,
and thus writing new code to process data feels easier and more natural to seismologists.
Another important aspect of this approach is that code processing data (i.e. functions) becomes
less coupled with code for reading and writing data (i.e. the data class). Therefore, Pysmo
functions are not affected by things such as changes in particular file formats and related
classes.

In order to view data this way while also using existing formats, we use Python
`protocol classes <https://docs.python.org/3/library/typing.html#typing.Protocol>`_ to define
Pysmo data types. These protocols exactly define the type of data a Pysmo function expects as
*input*. Pysmo functions can therefore be used with any data class that matches the
requirements imposed by the protocols. Put another way, as Pysmo functions are written
specifically for data types defined by protocols, compatible data classes essentially become
that type from the function's point of view. Typically an existing data class will not work
out of the box with Pysmo this way, and we need to extend the class to make it compatible
(Fig. :numref:`fig_pysmo_layer`). Crucially, this requires only a fraction of work compared
to writing a data class from scratch.

   .. _fig_pysmo_layer:
   .. figure:: images/pysmo_layer.drawio.png
      :align: center

      (a) An existing data class, when used as input for Pysmo functions, will
      likely **not** be compatible with the function.
      (b) After extending the data class it becomes compatible with more Pysmo
      functions.

.. note::
   Users new to Python may have learned that *everything* in Python is an object. But if
   objects are instances of a class, then what kind of object is a class itself? We can
   run the ``type`` command in a Python shell to find out - running it first on the
   number 42 tells us it is an instance of the ``int`` class:
      
      >>> type(42)
      <class 'int'> 

   Running ``type`` again, but this time on the ``int`` class we see that a class
   is an instance of ``type``:

      >>> type(int)
      <class 'type'>

   While this does not restrict what can or cannot go in a class, we still consider
   it to be worthwhile to keep this in mind in order to write meaningful classes in
   Python (i.e. is the class we are defining something we could reasonably describe
   as a "type"?).


Module Components
-----------------
In order to use Pysmo, it is useful to understand the three main
components:

   #. The Pysmo data types introduced above and discussed more in :ref:`protocols:protocol classes`.
   #. The Pysmo :ref:`functions:functions`, that use these data types for input and output. These
      functions are intentionally kept simple, in that they only perform a single task.
   #. :ref:`tools:tools` are more complex then Pysmo functions, potentially something making use of
      multiple Pysmo functions, requiring user interaction, etc.
