from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import Settings


@dataclass(slots=True)
class SmtpEmailConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    use_tls: bool
    timeout_seconds: int


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_email(self, *, to_email: str, subject: str, body: str) -> None:
        config = self._build_config()
        message = EmailMessage()
        message["From"] = config.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds) as client:
            client.ehlo()
            if config.use_tls:
                client.starttls()
                client.ehlo()
            if config.username is not None and config.password is not None:
                client.login(config.username, config.password)
            client.send_message(message)

    def _build_config(self) -> SmtpEmailConfig:
        host = (self.settings.smtp_host or "").strip()
        from_email = (self.settings.smtp_from_email or "").strip()
        username = (self.settings.smtp_username or "").strip() or None
        password = (self.settings.smtp_password or "").strip() or None

        if not host:
            raise ValueError("SMTP_HOST 缺失或为空，无法使用 smtp_email 通道。")
        if not from_email:
            raise ValueError("SMTP_FROM_EMAIL 缺失或为空，无法使用 smtp_email 通道。")
        if (username is None) != (password is None):
            raise ValueError("SMTP_USERNAME 与 SMTP_PASSWORD 必须同时配置或同时留空。")

        port = self._parse_positive_int(self.settings.smtp_port, "SMTP_PORT")
        timeout_seconds = self._parse_positive_int(self.settings.smtp_timeout_seconds, "SMTP_TIMEOUT_SECONDS")

        return SmtpEmailConfig(
            host=host,
            port=port,
            username=username,
            password=password,
            from_email=from_email,
            use_tls=self.settings.smtp_use_tls,
            timeout_seconds=timeout_seconds,
        )

    def _parse_positive_int(self, raw_value: str | None, field_name: str) -> int:
        text = (raw_value or "").strip()
        if not text:
            raise ValueError(f"{field_name} 缺失或为空，无法使用 smtp_email 通道。")
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} 必须是正整数，当前配置无效。") from exc
        if value <= 0:
            raise ValueError(f"{field_name} 必须是正整数，当前配置无效。")
        return value
