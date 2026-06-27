from flask import current_app
from flask_mail import Message

from app.extensions.mail import mail


def send_email(to: str, subject: str, body: str) -> None:
    if not to:
        return
    try:
        message = Message(subject=subject, recipients=[to], body=body)
        mail.send(message)
    except Exception as exc:  # noqa: BLE001 - email failures must never crash API
        current_app.logger.warning("Email delivery failed: %s", exc)
