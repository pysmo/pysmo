class SacHeaderUndefined(Exception):
    """Raised when requesting a value from a SAC header returns None.

    Attributes:
        message: Custom message to display.
        header: SAC header name to be used in the default exception message.
    """

    def __init__(self, message: str | None = None, header: str | None = None) -> None:
        self.message = f"Value for SAC header {header} is None."
        if message is not None:
            self.message = message
        super().__init__(self.message)
