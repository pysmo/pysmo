class Duck:  # (1)!
    def quack(self):
        return "quack, quack!"

    def waddle(self):
        return "waddle, waddle!"


class Human:  # (2)!
    def quack(self):
        return "quack, quack!"

    def waddle(self):
        return "waddle, waddle!"


def is_a_duck(thing):  # (3)!
    try:
        thing.quack()
        thing.waddle()
        print("I must be a duck!")
    except AttributeError:
        print("I'm unable to walk and talk like a duck.")
