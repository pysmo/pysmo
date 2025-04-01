from typing import Protocol


class EmailSender(Protocol):
    def send_email(self, email_address: str, message: str) -> None: ...


def signup(username: str, email_address: str, emailer: EmailSender) -> None:
    """Send a welcome email to a new user using 3rd party email service."""

    formatted_message = f"Hello {username}, welcome to the pysmo service!"
    emailer.send_email(email_address, formatted_message)
