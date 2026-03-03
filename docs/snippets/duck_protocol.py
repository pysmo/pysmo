from typing import Protocol


class Ducklike(Protocol):  # (1)!
    def quack(self) -> str: ...  # (2)!

    def waddle(self) -> str: ...


class Duck:  # (3)!
    def quack(self) -> str:
        return "quack, quack!"

    def waddle(self) -> str:
        return "waddle, waddle!"


class Human:  # (4)!
    def quack(self) -> str:
        return "quack, quack!"

    def waddle(self) -> str:
        return "waddle, waddle!"

    def dance(self) -> str:
        return "shaking those hips!"


class Robot:  # (5)!
    def quack(self) -> bytes:
        return bytes("beep, quack!", encoding="utf-8")

    def waddle(self) -> str:
        return "waddle, waddle!"


def is_a_duck(thing: Ducklike) -> None:  # (6)!
    try:
        thing.quack()
        thing.waddle()
        print("I must be a duck!")
    except AttributeError:
        print("I'm unable to walk and talk like a duck.")
