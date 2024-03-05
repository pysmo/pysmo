from typing import Protocol  # (1)!


class Ducklike(Protocol):  # (2)!
    def quack(self) -> str:  # (3)!
        ...

    def waddle(self) -> str: ...


class Duck:  # (4)!
    def quack(self) -> str:
        return "quack, quack!"

    def waddle(self) -> str:
        return "waddle, waddle!"


class Human:  # (5)!
    def quack(self) -> str:
        return "quack, quack!"

    def waddle(self) -> str:
        return "waddle, waddle!"

    def dance(self) -> str:
        return "shaking those hips!"


class Robot:  # (6)!
    def quack(self) -> bytes:
        return bytes("beep, quack!", "UTF-8")

    def waddle(self) -> str:
        return "waddle, waddle!"


def is_a_duck(thing: Ducklike) -> None:  # (7)!
    try:
        thing.quack()
        thing.waddle()
        print("I must be a duck!")
    except AttributeError:
        print("I'm unable to walk and talk like a duck.")
