import os
import smtplib
from email.message import EmailMessage


class EmailConfigurationError(RuntimeError):
    pass


def send_email(recipient: str, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise EmailConfigurationError(
            "Email delivery is not configured. Set SMTP_HOST and SMTP_FROM."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    timeout = int(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    try:
        if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                if username:
                    smtp.login(username, password or "")
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
                    smtp.starttls()
                if username:
                    smtp.login(username, password or "")
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailConfigurationError("Email delivery failed.") from error
