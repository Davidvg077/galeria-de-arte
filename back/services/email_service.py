class EmailConfigurationError(RuntimeError):
    pass


def send_email(recipient: str, subject: str, body: str) -> None:
    raise EmailConfigurationError("Modo demostración: no se envían correos reales.")
