"""Booking confirmations: optional SMTP e-mail + WhatsApp click-to-chat links."""
import logging
import smtplib
import threading
from email.message import EmailMessage
from urllib.parse import quote

from .config import settings

log = logging.getLogger("slotease.notify")


def wa_link(phone: str, text: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:  # assume India if no country code
        digits = "91" + digits
    return f"https://wa.me/{digits}?text={quote(text)}" if digits else ""


def _send_email(to: str, subject: str, body: str) -> None:
    try:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        log.info("Confirmation e-mail sent to %s", to)
    except Exception as exc:  # noqa: BLE001 - notifications must never break booking
        log.warning("E-mail to %s failed: %s", to, exc)


def send_confirmation(to_email: str | None, subject: str, body: str) -> str:
    """Returns the channel used: 'email' or 'log'."""
    log.info("CONFIRMATION -> %s | %s | %s", to_email or "-", subject, body)
    if settings.smtp_host and to_email:
        threading.Thread(target=_send_email, args=(to_email, subject, body), daemon=True).start()
        return "email"
    return "log"
