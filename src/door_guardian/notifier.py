"""SMTP notification support without embedded credentials."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from .config import Settings


class NotificationError(RuntimeError):
    """Raised when a configured notification cannot be delivered."""


class EmailNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return all(
            [
                self.settings.smtp_host,
                self.settings.smtp_username,
                self.settings.smtp_password,
                self.settings.smtp_sender,
                self.settings.smtp_recipient,
            ]
        )

    def send_intruder_alert(self, reason: str = "人脸识别未通过") -> bool:
        if not self.configured:
            return False

        message = EmailMessage()
        message["Subject"] = "智能门神：陌生人到访提醒"
        message["From"] = self.settings.smtp_sender
        message["To"] = self.settings.smtp_recipient
        message.set_content(f"检测到一次未授权访问。原因：{reason}")

        try:
            if self.settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    context=context,
                    timeout=10,
                ) as client:
                    client.login(
                        self.settings.smtp_username, self.settings.smtp_password
                    )
                    client.send_message(message)
            else:
                with smtplib.SMTP(
                    self.settings.smtp_host, self.settings.smtp_port, timeout=10
                ) as client:
                    client.starttls(context=ssl.create_default_context())
                    client.login(
                        self.settings.smtp_username, self.settings.smtp_password
                    )
                    client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise NotificationError(str(exc)) from exc
        return True

