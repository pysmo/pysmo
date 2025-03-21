from emailprovider import EmailProvider


def signup(username: str, email_address: str, emailer: EmailProvider) -> None:
    """Send a welcome email to a new user using 3rd party email service."""

    formatted_message = f"Hello {username}, welcome to the pysmo service!"
    emailer.send_email(email_address, formatted_message)
