# Introduction

## Rationale

Anyone who has taken a course on programming (in any language) will most likely
first have been taught about the different data types available. These typically
consist of simple types like integers, floats, strings, as well as the more
complicated arrays, dictionaries, etc. These types are typically very clearly
defined and intuitive to use. For example, we don't need to think very hard
whether or not it makes sense to pass the string "hello world" as input to a
program that calculates the square root of numbers. That simply doesn't make
much sense, and not just within a piece of code, but also when using pen and
paper.

As one moves from general-purpose programming towards more specialised problem
solving (e.g. within a particular scientific field), the expected input (and
output) for a piece of code is likely to become more complex. We may therefore
quite easily reach a point where we no longer have that intuitive feeling about
the data we are working with. In seismology this effect may be compounded by the
fact that different file formats (and thus definitions) for seismograms exist.

Pysmo aims to mitigate this by defining types that make sense for seismological
problems the same way the built-in types make sense for general-purpose
programming. This is implemented by differentiating between how data are stored,
and how they are processed. As a matter of fact, the focus is pretty much
exclusively on how they are processed. The two main reasons for this are:

- The vast majority of code we write deals with processing data, not storing.
- When we are processing data, we are typically thinking of data more in terms
  of what they represent in the physical world. This is less so when storing
  data, as we are then less interested in capturing only the essence of e.g.
  a seismogram, but rather want to add as much useful metadata as possible,
  combine different data sources into one large object, etc.

## A Software Contract

When we write software, we often need to pass information around between
different parts of our code. To do this, the different parts need to be in
an agreement about the type of data they are going to exchange. One could say
that a contract exists that needs to be followed for our code to work properly.
In Python we can use type hints to describe such a contract. In the simplest
case, the information that is being exchanged consists of a built-in type such
as a [`float`][float]:

```python
def times_two(input_variable: float) -> float:
    """Returns input variable multiplied by 2."""

    return input_variable * 2
```

The above function makes it quite clear what the contract for its usage is: it
expects a [`float`][float] as as input, and it returns a [`float`][float] as
output. If we try to call this function in other parts of our code using e.g. a
[`str`][str] as input, our code editor will notify us that we made a mistake
before we even run our program! The same is true for the function output - if
we use the output as if it were a [`str`][str], we would again get an error
message from our code editor.

Things get more challenging when the information passed around is not just
a built-in type, but instead a piece of code itself. To illustrate this, lets
imagine a hypothetical function that is used to sign up a new user for our
service, and sends them an email for confirmation. The function does not itself
send the email, but instead uses a 3rd party module passed as an argument to
the function. Our code may look something like this:

```python title="signup.py"
--8<-- "docs/snippets/signup.py"
```

The contract here, again expressed using type hints (and by using the
`send_email` method of the `EmailProvider` class...), is between our `signup`
function and the 3rd party module. The contract is also quite specifically with
this particular email service provider. This means our function is strongly
coupled with this 3rd party module. An easy way to tell this would be to remove
the first line from the above code - your code editor would straight away
complain that `EmailProvider` is not defined. Should the email provider go out
of business, or even just change their API (i.e. how their module works), our
code would break. This is likely an easy fix if we use this email provider in
just one place, but if we have multiple functions that make use of this module,
they will all need to be refactored too. This would potentially be a lot of
work, which can be avoided by writing the contract outside of the function(s).
This contract would only need to be written once. If you remember the
[first-steps](/first-steps) section, you'll likely guess that this way of
defining the contract is by using [`Protocol`][typing.Protocol] classes:

```python title="signup2.py"
--8<-- "docs/snippets/signup2.py"
```

Now there exists a contract between the `signup` function and the `EmailSender`
class. Any third party email provider we might want to use will need to fulfill
a contract with the `EmailSender` class instead of the `signup` function. Here,
the `EmailSender` class doesn't do anything by itself. Instead it describes
what a generic "class that can send emails" should look like in order to work
with the `signup` function. The `EmailSender` class is only used by the type
checker in your code editor, so it cannot be used in parts of the code that
actually do things (i.e. you cannot create an instance of the `EmailSender`
class). Instead you use a generic class that matches what `EmailSender`
prescribes to actually perform the desired `send_email` action:

<!-- skip: next -->

```python
from emailprovider import EmailProvider #(1)!
from emailprovider2 import EmailProvider2 #(2)!
from signup import signup as signup1
from signup2 import signup as signup2

emailer1 = EmailProvider()
emailer2 = EmailProvider2()
new_user = "joe"
new_user_email = "joe@example.com"

signup1(new_user, new_user_email, emailer1) #(3)!
signup1(new_user, new_user_email, emailer2) #(4)!
signup2(new_user, new_user_email, emailer1) #(5)!
signup2(new_user, new_user_email, emailer2) #(6)!
```

1. This is the email provider that is also used in `signup.py`.
2. This is another 3rd party email provider. We assume it also has a
   `send_email` method.
3. Our type checker will be happy with this - all contracts are fulfilled.
4. Type checker will complain - `signup1` expects `EmailProvider`, but got
   `EmailProvider2`.
5. Type checker is happy with this - `signup2` doesn't expect any particular
   email provider class, but whichever one provided must have a `send_email`
   method.
6. Type checker is happy with this - `EmailProvider2` has a `send_email` method.

To summarise, we can describe Python's typing system as contracts with the
following two important properties:

- They are only used by type checkers that scan code rather than executing it.
  They are ignored at runtime.
- We can define intermediary contracts with [Protocol][typing.Protocol]
  classes. These serve as interfaces that describe how information is
  exchanged (hence the name "protocol").

!!! tip

    If you are still not sure what protocols are (or why they are so useful),
    consider how ubiquitous email is despite the existance of a myriad of
    alternatives for communicating in todays digital world. The likely reason
    for this success is interoperability: we can freely email each other using
    different work or private email addresses, and we can do so using various
    email clients or webmail. This is only possible because the way emails are
    sent and received is prescribed by protocols. These protocols define a
    common standard that allows using email everywhere, without needing to be
    concerned about things such as differences between the inner workings of
    different types of email servers.

## What does pysmo do?

What we haven't discussed so far is how [Protocol][typing.Protocol] classes
allow us to be very specific about what we need (and also don't need) for our
code to run. Consider the two email providers we used in the example above:
perhaps `EmailProvider` can only send emails, while `EmailProvider2` also is
able to receive emails using a `receive_email` method. However, as this method
is not specified in our `EmailSender` class, we can safely ignore this difference
and use both email providers interchangeably. Should we at some point in the
future need to receive emails, we would just create a `EmailReceiver` protocol
for that purpose. We would then have two smaller contracts with
`EmailProvider2` instead of one big one.

In seismology, a seismogram is typically a time series with some metadata
attached to it. What these metadata are, often varies between different file
types or use cases. Consider for example the
[SAC](https://ds.iris.edu/files/sac-manual/manual/file_format.html) file
format: it contains over 150 different header fields, of which only six are
required (granted, some of those 150 are unused). This probably makes a lot of
sense for storing data, or using SAC files with the SAC application. However, it
also means we can never be certain about exactly what information is contained
in a given SAC file. This is not dissimilar to the example with two different
email providers. There, we dealt with it by defining ourselves what an email
sender should look like.

In pysmo we do exactly the same thing, but for types relevant to seismology.
Pysmo forms the contract between areas where we want to add lots of detail to
our data (e.g. when storing data, or within an application) and general-purpose
processing of data where we typically don't care about metadata. For example,
one of the most basic operations is applying a filter to a seismogram. Rather
than writing an implementation for it over and over again for different types
of seismograms, we can define a common interface for them and then use the same
implementation all the time.

At its core, pysmo is simply a set of contracts that allow writing code for a
very simple and narrow definition of e.g. a seismogram, and then re-using that
same code for a seismogram that is highly specific in its implementation.

!!! tip

    <a id="type-tip"></a>
    Above we used the terms contract, type and protocol somewhat
    interchangeably. Hopefully it is clear that pieces of software don't
    actually sign contracts between them; we just used the term to express
    how they depend on each other and are thus coupled. That leaves us with
    types and (protocol) classes. Let's explore their relationship using the
    built-in float type as an example:

    ```python
    >>> a = 1.2 #(1)!
    >>> type(a) #(2)!
    <class 'float'>
    >>> type(float) #(3)!
    <class 'type'>
    >>>
    ```

    1. We first assign a float to the variable `a`.
    2. Then we verify it is indeed a float using the `type` command.
    3. The type of the float class is...

    Remember, in Python everything is an object. So in the above snippet we
    created an object called `a` of the [`float`][float] class (objects are
    instances of a class). Where it gets interesting, is when we query what type
    our variable `a` is using the [`type`][type] command; instead of returning
    simply "float", the Python interpreter tells us the type of `a` is `<class
    'float'>`. In other words, the [`float`][float] class is itself a type
    (which we verify in the last line). Simply put then, every time we define a
    class in Python, we also define a type.

## Use Cases

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
